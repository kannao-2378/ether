import copy
import json
import tempfile
import unittest
import uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,text
import app
import starter_course as starter
import curriculum_engine as ce


class StarterCourseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=create_engine('sqlite:///'+str(Path(self.tmp.name)/'test.db'))
        app.initialize(self.db,with_bulk=False)
        with self.db.begin() as c:
            c.execute(text('CREATE TABLE test_clock(id INTEGER PRIMARY KEY,days INTEGER,stage INTEGER)'))
            c.execute(text('INSERT INTO test_clock VALUES(1,0,1)'))
        self.patch=patch.object(app,'test_engine',self.db);self.patch.start()
        self.client=TestClient(app.app);self.headers={'X-Learning-Test':'1'}
        self.stamp=datetime(2026,11,4,8,tzinfo=timezone.utc)
        self.clock=patch('app.now',side_effect=lambda:self.stamp);self.clock.start()

    def tearDown(self):
        self.client.close();self.clock.stop();self.patch.stop();self.db.dispose();self.tmp.cleanup()

    def post(self,path,data=None):
        r=self.client.post(path,json=data or {},headers=self.headers)
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def activate(self):return self.post('/api/test/starter-course')

    def targets(self):
        with self.db.connect() as c:
            return [dict(r) for r in c.execute(text("SELECT k.* FROM curriculum_lessons l JOIN curriculum_paths p ON p.goal_id=l.goal_id JOIN knowledge k ON k.id=l.knowledge_id WHERE p.course_id='starter-preview' AND l.role='transfer'")).mappings()]

    def test_validation_detects_teaching_answer_leak_and_missing_material(self):
        spec=starter.load();self.assertEqual(len(spec['goals']),7)
        bad=copy.deepcopy(spec);bad['goals'][0]['usage']='I want to learn English.'
        with self.assertRaises(ValueError):starter.validate(bad)
        bad=copy.deepcopy(spec);bad['goals'][-1]['variants'][0]['requires']=['not-a-goal']
        with self.assertRaises(ValueError):starter.validate(bad)

    def test_real_mode_forbidden_and_does_not_publish(self):
        with app.real_engine.connect() as c:before=c.execute(text('SELECT count(*) FROM answers')).scalar()
        r=self.client.post('/api/test/starter-course',json={})
        self.assertEqual(r.status_code,403)
        with app.real_engine.connect() as c:
            self.assertFalse(starter.enabled(c));self.assertEqual(c.execute(text('SELECT count(*) FROM answers')).scalar(),before)

    def test_existing_test_history_requires_explicit_reset(self):
        with self.db.begin() as c:c.execute(text("UPDATE progress SET introduced=1 WHERE knowledge_id='word-i'"))
        r=self.client.post('/api/test/starter-course',json={},headers=self.headers)
        self.assertEqual(r.status_code,409)
        with self.db.connect() as c:
            self.assertFalse(starter.enabled(c));self.assertEqual(c.execute(text("SELECT introduced FROM progress WHERE knowledge_id='word-i'")).scalar(),1)

    def test_activation_no_fake_mastery_or_extra_variants_and_idempotent(self):
        r=self.activate();self.assertEqual(len(r['starter_course']['groups']),7)
        self.assertEqual(len(self.targets()),3)
        with self.db.connect() as c:
            self.assertEqual(c.execute(text('SELECT count(*) FROM answers')).scalar(),0)
            self.assertEqual(c.execute(text('SELECT count(*) FROM progress WHERE introduced=1 OR level>0')).scalar(),0)
            before=[tuple(r) for r in c.execute(text('SELECT * FROM progress'))]
            self.assertEqual(c.execute(text("SELECT count(*) FROM curriculum_goals WHERE status='ready'")).scalar(),7)
        self.activate()
        with self.db.connect() as c:self.assertEqual(before,[tuple(r) for r in c.execute(text('SELECT * FROM progress'))])

    def test_normal_http_learning_reaches_unseen_transfer_and_retains_results(self):
        self.activate();transfers=[];seen_cards=[]
        for n in range(240):
            q=self.post('/api/next')
            if q['kind']=='done':
                if len(set(transfers))==3:break
                self.stamp+=timedelta(days=1)
                continue
            if q['kind']=='learn':
                detail=self.client.get('/api/knowledge/'+q['id']+'?visible=true',headers=self.headers).json()
                text_body=json.dumps(detail,ensure_ascii=False)
                for target in self.targets():self.assertNotIn(target['answer'],text_body)
                self.post('/api/introduce/'+q['id']);seen_cards.append(q['id']);continue
            self.assertNotIn('answer',q)
            with self.db.connect() as c:answer=c.execute(text('SELECT answer FROM knowledge WHERE id=:k'),dict(k=q['id'])).scalar()
            if q['group_role']=='transfer':
                self.assertIn(q['exercise_mode'],('transfer','transfer-review'))
                transfers.append(q['id'])
            checked=self.post('/api/check',dict(id=str(uuid.uuid4()),question_id=q['question_id'],answer=answer.lower()))
            self.assertTrue(checked['correct'])
            # The real UI opens the explanation after a correct check and before
            # confidence feedback. The trial's pre-answer mode must be retained.
            self.client.get('/api/knowledge/'+q['id']+'?visible=true',headers=self.headers)
            self.post('/api/answers',dict(question_id=q['question_id'],answer=answer.lower(),confidence='clear'))
        self.assertEqual(len(set(transfers)),3,dict(transfers=transfers,seen=seen_cards))
        with self.db.connect() as c:
            self.assertGreater(c.execute(text('SELECT count(*) FROM memory_states')).scalar(),0)
            self.assertEqual(c.execute(text("SELECT count(DISTINCT a.knowledge_id) FROM answers a JOIN question_trials q ON q.question_id=a.question_id WHERE q.mode IN ('transfer','transfer-review')")).scalar(),3)
            before=[tuple(r) for r in c.execute(text('SELECT * FROM answers'))]
            summary=dict(request_iterations=n+1,answer_rows=len(before),
                         transfer_cards=len(set(transfers)),memory_cards=c.execute(text('SELECT count(*) FROM memory_states')).scalar(),
                         separate_learning_dates=c.execute(text("SELECT count(DISTINCT date(created_at)) FROM answers")).scalar(),
                         used_real_database=False)
        output=Path(app.DATA)/'starter-positive-flow.json'
        output.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        # Reopening initialization must retain results and the authored scope.
        app.initialize(self.db,with_bulk=False)
        with self.db.connect() as c:self.assertEqual(before,[tuple(r) for r in c.execute(text('SELECT * FROM answers'))])
        self.assertEqual(len(self.targets()),3)

    def test_material_forgotten_blocks_only_its_transfer_and_hint_not_independent(self):
        self.activate()
        with self.db.begin() as c:
            ids=starter.state(c)['ids']
            c.execute(text("UPDATE progress SET introduced=1,level=3,last_at=:t WHERE knowledge_id IN (SELECT knowledge_id FROM curriculum_lessons WHERE role!='transfer')"),dict(t=self.stamp.isoformat()))
            c.execute(text('UPDATE progress SET level=1 WHERE knowledge_id=:k'),dict(k=ids['starter-read-books']))
            for row in self.targets():
                permitted=app.group_learning.requirements_met(c,row['id'],stamp=self.stamp)
                self.assertEqual(permitted,'read books' not in row['answer'])
        target=next(r for r in self.targets() if 'learn English' in r['answer'])
        blocked=next(r for r in self.targets() if 'read books' in r['answer'])
        self.assertEqual(self.client.post('/api/challenge/'+blocked['id'],json={},headers=self.headers).status_code,409)
        q=self.post('/api/challenge/'+target['id'])
        self.post('/api/reveal/'+q['question_id'])
        self.post('/api/answers',dict(question_id=q['question_id'],answer=target['answer'],confidence='clear'))
        with self.db.connect() as c:self.assertEqual(app.assessment.calculate(c,ids['starter-want-to'])['transfer_successes'],0)

    def test_reset_exit_and_conflicting_preview_guards(self):
        self.activate()
        r=self.client.post('/api/test/unlock',json={'stage':4},headers=self.headers)
        self.assertEqual(r.status_code,409)
        self.post('/api/test/reset')
        with self.db.connect() as c:
            self.assertTrue(starter.enabled(c));self.assertIsNone(c.execute(text('SELECT stage FROM test_clock')).scalar())
        self.post('/api/test/starter-exit')
        with self.db.connect() as c:
            self.assertFalse(starter.enabled(c))
            self.assertEqual(c.execute(text("SELECT count(*) FROM curriculum_paths p JOIN curriculum_goals g ON g.id=p.goal_id WHERE p.course_id='foundation' AND g.status='ready' AND p.authored=1")).scalar(),50)
            self.assertEqual(c.execute(text('SELECT count(*) FROM answers')).scalar(),0)

    def test_activation_with_packaged_dictionary_keeps_preview_scope(self):
        app.initialize(self.db,with_bulk=True)
        self.activate()
        with self.db.connect() as c:
            self.assertGreater(c.execute(text('SELECT count(*) FROM knowledge')).scalar(),13000)
            self.assertEqual(c.execute(text("SELECT count(*) FROM curriculum_goals WHERE status='ready'")).scalar(),7)
            self.assertLess(len(json.dumps(starter.state(c))),30000)
        self.assertEqual(len(self.targets()),3)

    def test_old_sourced_pilot_cannot_reappear_in_starter_after_reopening(self):
        with self.db.begin() as c:app.sourced_transfer.activate(c)
        self.activate()
        app.initialize(self.db,with_bulk=False)
        self.assertEqual(len(self.targets()),3)
        with self.db.connect() as c:self.assertFalse(app.sourced_transfer.enabled(c))


if __name__=='__main__':unittest.main()
