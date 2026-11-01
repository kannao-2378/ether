"""Original introductory lesson, with reference links rather than copied exercises."""
STEPS=[
 dict(id='meaning',kind='choice',prompt='你想表达“我想喝水”，应该使用哪种结构？',options=['I want + 东西','I want to + 动作原形'],answers=['I want to + 动作原形'],explanation='喝水是动作，所以用 want to drink。want 后直接接 water 表示想要水。'),
 dict(id='object',kind='write',prompt='我想要水。（直接说想要的东西）',answers=['I want water.','I want water'],explanation='I 是谁，want 是主要动词，water 是想要的东西。'),
 dict(id='collocation',kind='write',prompt='想要做某事：写出固定搭配，不写具体动作。',answers=['want to'],explanation='want to 后接动词原形。to 在这个结构里连接要做的动作。'),
 dict(id='phrase',kind='write',prompt='想喝水：写出动作短语。',answers=['want to drink water'],explanation='drink water 是喝水；want to 后接 drink，不用 drinking。'),
 dict(id='sentence',kind='write',prompt='我想喝水：写出完整句子。',answers=['I want to drink water.','I want to drink water'],explanation='I + want to + drink water。句首 I 大写，完整句子通常使用句末标点。'),
 dict(id='transfer',kind='write',prompt='换一个情境：你正在制定学习计划。写出“我想学英语”。',answers=['I want to learn English.','I want to learn English'],explanation='把 drink water 换成 learn English，仍然使用 I want to + 动作原形。'),
]
RULES=dict(title='第一课：想要东西，还是想做事情？',goal='分清 want 后接东西和 want to 后接动作，并独立换内容表达。',points=['想要一个东西：I want + 东西。例：I want water.','想做一件事：I want to + 动词原形。例：I want to drink water.','I 表示“我”；want 是主要动词；drink water 是想做的动作。','范围提醒：不是所有动词后都用 to。例如 enjoy 后接 doing；这一课只练 want。'],vocabulary=['water＝水','drink＝喝','learn English＝学英语'],sources=[dict(title='剑桥 Essential Grammar in Use 第三版目录：第5、52单元',url='https://assets.cambridge.org/97805216/75819/frontmatter/9780521675819_frontmatter.pdf'),dict(title='British Council：动词后接 doing 或 to do',url='https://learnenglish.britishcouncil.org/free-resources/grammar/a1-a2/verbs-followed-ing-or-infinitive')])

def normalize(value):return ' '.join(value.strip().split()).casefold().rstrip('.')

def install(c,text):
 c.execute(text('CREATE TABLE IF NOT EXISTS lesson_attempts(id TEXT PRIMARY KEY,lesson TEXT,step INTEGER,answer TEXT,correct INTEGER,hinted INTEGER,created_at TEXT)'))

def state(c,text):
 step=0
 for index in range(len(STEPS)):
  if c.execute(text("SELECT 1 FROM lesson_attempts WHERE lesson='want-01' AND step=:s AND correct=1 LIMIT 1"),dict(s=index)).first():step=index+1
  else:break
 return dict(step=step,total=len(STEPS),complete=step==len(STEPS),rules=RULES,question=({k:v for k,v in STEPS[step].items() if k not in ('answers','explanation')} if step<len(STEPS) else None))
