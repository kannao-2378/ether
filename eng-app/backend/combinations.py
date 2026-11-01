"""Reviewed combinations, not unrestricted text concatenation."""
MATERIALS=[
 ('drink-water','喝水','drink water','drink 是原形，water 是动作对象。'),
 ('enjoy-reading','享受阅读的乐趣','enjoy reading','enjoy 是原形，后面仍用 reading；不是把 reading 直接接到 want to 后。'),
 ('read-books','读书','read books','read 是原形；区别于 enjoy 后的 reading。'),
]
COMBINATIONS=[
 ('want-to-transfer-drink','drink-water','我想喝水。','drink water'),
 ('want-to-transfer-enjoy-reading','enjoy-reading','我想享受阅读的乐趣。','enjoy reading'),
 ('want-to-transfer-read','read-books','我想读书（使用 read books）。','read books'),
]

def install(c,text):
 c.execute(text('CREATE TABLE IF NOT EXISTS sentence_combinations(knowledge_id TEXT PRIMARY KEY,structure_id TEXT,material_id TEXT,reviewed INTEGER)'))
 for kid,prompt,answer,explanation in MATERIALS:
  c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:p,:a,:e,:x)'),dict(k=kid,p=prompt,a=answer,e=explanation,x=answer))
  c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
 for kid,material,prompt,action in COMBINATIONS:
  answer='I want to '+action+'.'
  c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:p,:a,:e,:x)'),dict(k=kid,p=prompt,a=answer,e='使用相同的 I want to 结构，连接已学动作。这里 to 后的第一个动词使用原形。',x=answer))
  c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
  c.execute(text("INSERT OR IGNORE INTO course_links VALUES(:k,'want-to-sentence',4,'已审核的结构与材料组合')"),dict(k=kid))
  c.execute(text('INSERT OR IGNORE INTO transfer_materials VALUES(:k,:m)'),dict(k=kid,m=material))
  c.execute(text("INSERT OR IGNORE INTO sentence_combinations VALUES(:k,'want-to',:m,1)"),dict(k=kid,m=material))
 # Existing situations participate in the same structure family.
 for kid,material in [('want-to-transfer','learn-english'),('want-to-transfer-school','go-to-school'),('want-to-transfer-eat','eat-a-meal')]:
  c.execute(text("INSERT OR IGNORE INTO sentence_combinations VALUES(:k,'want-to',:m,1)"),dict(k=kid,m=material))
