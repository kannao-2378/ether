import copy
import json
import random
import tempfile
import unittest
import uuid
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,text
import app
import starter_course as course
import curriculum_engine as ce
import selection_cache


class MainlineCourseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'mainline.db'))
        app.initialize(self.db,with_bulk=False)
        with self.db.begin() as c:
            c.execute(text('CREATE TABLE test_clock(id INTEGER PRIMARY KEY,days INTEGER,stage INTEGER)'))
            c.execute(text('INSERT INTO test_clock VALUES(1,0,NULL)'))
        self.engine_patch=patch.object(app,'test_engine',self.db);self.engine_patch.start()
        self.client=TestClient(app.app);self.headers={'X-Learning-Test':'1'}
        self.clock=patch('app.now',return_value=datetime(2026,11,4,9,tzinfo=timezone.utc));self.clock.start()

    def tearDown(self):
        self.clock.stop();self.client.close();self.engine_patch.stop();self.db.dispose();self.tmp.cleanup()

    def post(self,path,data=None):return self.client.post(path,json=data or {},headers=self.headers)

    def activate(self):
        r=self.post('/api/test/mainline-course');self.assertEqual(r.status_code,200,r.text);return r.json()['starter_course']

    def test_all_topics_objectives_materials_and_graph(self):
        spec=course.load('mainline')
        self.assertEqual(len(spec['goals']),148)
        self.assertEqual(len({o['id'] for o in spec['objective_tasks']}),729)
        self.assertFalse(spec['assessment_policy']['automatic_full_objective_certification'])
        keys={g['key'] for g in spec['goals']}
        self.assertEqual(len(keys),148)
        self.assertTrue(all(set(g['requires'])<=keys for g in spec['goals']))
        self.assertTrue(all(m['zh'] and m['usage'] for g in spec['goals'] for m in g['materials']))
        bad=copy.deepcopy(spec);bad['goals'][0]['requires']=[bad['goals'][-1]['key']]
        with self.assertRaises(ValueError):course.validate(bad)

    def test_activation_permissions_no_fake_grades_and_restart(self):
        self.assertEqual(self.client.post('/api/test/mainline-course',json={}).status_code,403)
        r=self.activate();self.assertEqual(len(r['groups']),148);self.assertEqual(r['transfer_questions'],294)
        with self.db.connect() as c:
            self.assertEqual(c.execute(text('SELECT count(*) FROM answers')).scalar(),0)
            self.assertEqual(c.execute(text('SELECT count(*) FROM progress WHERE introduced=1 OR level>0')).scalar(),0)
            before=[tuple(r) for r in c.execute(text('SELECT * FROM progress'))]
        app.initialize(self.db,with_bulk=False)
        with self.db.connect() as c:
            self.assertEqual(before,[tuple(r) for r in c.execute(text('SELECT * FROM progress'))])
            self.assertEqual(len(course.report(c)['groups']),148)
        self.assertEqual(self.post('/api/test/starter-course').status_code,409)
        self.assertEqual(self.post('/api/test/unlock',{'stage':4}).status_code,409)

    def test_first_real_requests_only_start_with_available_materials(self):
        self.activate()
        seen=[]
        for _ in range(16):
            r=self.post('/api/next');self.assertEqual(r.status_code,200,r.text);q=r.json()
            self.assertNotEqual(q['kind'],'done',q)
            if q['kind']=='learn':
                seen.append(q['id']);self.assertEqual(self.post('/api/introduce/'+q['id']).status_code,200)
            else:
                self.assertNotIn('answer',q)
                with self.db.connect() as c:answer=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),{'k':q['id']}).scalar()
                checked=self.post('/api/check',dict(id=str(uuid.uuid4()),question_id=q['question_id'],answer=answer))
                self.assertTrue(checked.json()['correct'],checked.text)
                saved=self.post('/api/answers',dict(question_id=q['question_id'],answer=answer,confidence='clear'))
                self.assertEqual(saved.status_code,200,saved.text)
        self.assertTrue(seen)
        with self.db.connect() as c:self.assertGreater(c.execute(text('SELECT count(*) FROM answers')).scalar(),0)

    def test_all_context_dependencies_and_sample_real_grading(self):
        self.activate();rng=random.Random(1104)
        with self.db.connect() as c:
            candidates=c.execute(text("SELECT DISTINCT l.knowledge_id FROM curriculum_lessons l JOIN curriculum_paths p ON p.goal_id=l.goal_id WHERE p.course_id=:c AND l.role='transfer'"),{'c':course.COURSE}).scalars().all()
            self.assertEqual(len(candidates),294)
            for kid in candidates:self.assertFalse(course.can_challenge(c,kid,app.now()))
        # An isolated synthetic prerequisite fixture exercises every compiled
        # dependency. It is not a claim of 148 lessons learned by a person.
        with self.db.begin() as c:
            c.execute(text("UPDATE progress SET level=3,introduced=1,last_at=:t WHERE knowledge_id NOT IN (SELECT knowledge_id FROM curriculum_lessons WHERE role='transfer')"),{'t':app.now().isoformat()})
        selection_cache.invalidate()
        with self.db.connect() as c:
            for kid in candidates:self.assertTrue(course.can_challenge(c,kid,app.now()),kid)
        sampled=rng.sample(candidates,16)
        modes=[]
        for kid in sampled:
            q=self.post('/api/challenge/'+kid);self.assertEqual(q.status_code,200,q.text);q=q.json()
            self.assertNotIn('answer',q)
            with self.db.connect() as c:
                answer=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),{'k':kid}).scalar()
                modes.append(c.execute(text('SELECT mode FROM question_trials WHERE question_id=:q'),{'q':q['question_id']}).scalar())
            if kid==sampled[0]:
                wrong=self.post('/api/check',dict(id=str(uuid.uuid4()),question_id=q['question_id'],answer='nottherightanswer'))
                self.assertFalse(wrong.json()['correct'])
            result=self.post('/api/check',dict(id=str(uuid.uuid4()),question_id=q['question_id'],answer=answer.lower()))
            self.assertTrue(result.json()['correct'],result.text)
            saved=self.post('/api/answers',dict(question_id=q['question_id'],answer=answer,confidence=rng.choice(['clear','hard','forgot'])))
            self.assertEqual(saved.status_code,200,saved.text)
        with self.db.connect() as c:
            self.assertEqual(c.execute(text('SELECT count(*) FROM answers')).scalar(),16)
            self.assertGreater(c.execute(text('SELECT count(*) FROM memory_states')).scalar(),0)
        self.assertIn('transfer',modes)
        log=Path(app.DATA_DIR)/'mainline-validation.json' if hasattr(app,'DATA_DIR') else Path(self.tmp.name)/'mainline-validation.json'
        log.write_text(json.dumps(dict(topics=148,context_gates_checked=294,sampled_answers=16,seed=1104,
            fixture='synthetic prerequisites in temporary database',real_data_used=False)),encoding='utf-8')

    def test_exit_preserves_answer_rows_and_original_course(self):
        self.activate()
        self.assertEqual(self.post('/api/test/starter-exit').status_code,200)
        with self.db.connect() as c:
            self.assertFalse(course.enabled(c))
            self.assertEqual(c.execute(text("SELECT count(*) FROM curriculum_goals WHERE status='ready'")).scalar(),50)
            self.assertEqual(c.execute(text('SELECT count(*) FROM answers')).scalar(),0)


if __name__=='__main__':unittest.main()
