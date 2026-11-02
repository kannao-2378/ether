import re

def normalize(s):
 return re.sub(r'\s+',' ',s.strip().replace('’',"'")).casefold().rstrip('.!?。！？').rstrip()

def answer_options(kid,expected,alternatives=None):
 variants={
  'want-to-transfer-eat':['I want to eat.','I want to have a meal.','I want to eat a meal.'],
  'want-to-transfer-school':['I want to go to school.'],
 }
 valid=alternatives or variants.get(kid,[expected])
 return valid

def grade(kid,answer,expected,alternatives=None):
 norm=normalize
 valid=answer_options(kid,expected,alternatives)
 correct=norm(answer) in [norm(s) for s in valid]
 errors=[]
 if not correct:
  if norm(answer).startswith('i want to '):
   errors.append('I want to 句型使用正确，需要检查后面的动作表达。')
  if re.search(r'\bgo school\b',norm(answer)):
   errors.append('“去学校”是 go to school，这里缺少 to；不是 want to 句型错误。')
  if not errors:errors.append('请检查主语、动词接法和拼写；本题使用课程内已审核的答案集合，暂不支持任意自由表达批改。')
 notices=[]
 if correct:
  if re.search(r'\bi\b',answer):notices.append('书写提示：表示“我”的 I 要大写。')
  if expected[:1].isupper() and answer.strip()[:1].islower():notices.append('书写提示：句首字母要大写。')
  if expected.endswith(('.', '?', '!')) and not answer.strip().endswith(('.', '?', '!', '。','？','！')):notices.append('书写提示：完整句子建议添加句末标点。')
 return dict(correct=correct,analysis=errors,notices=notices)

def install(c,text):
 c.execute(text('CREATE TABLE IF NOT EXISTS transfer_materials(knowledge_id TEXT,material_id TEXT,PRIMARY KEY(knowledge_id,material_id))'))
 for kid,prompt,answer in [('go-to-school','去学校','go to school'),('eat-a-meal','吃饭（使用 eat）','eat'),('learn-english','学英语','learn English')]:
  c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:p,:a,:e,:x)'),dict(k=kid,p=prompt,a=answer,e={'go-to-school':'go 是去，school 是学校；去学校要写 go to school，中间的 to 不能省。','eat-a-meal':'eat 可以表示吃饭，也能在后面接吃的食物。','learn-english':'learn 是学，English 是英语；learn English 连起来就是学英语。'}[kid],x=answer))
  c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
  c.execute(text('UPDATE knowledge SET explanation=:e WHERE id=:k AND explanation=:old'),dict(k=kid,e={'go-to-school':'go 是去，school 是学校；去学校要写 go to school，to 不能省。','eat-a-meal':'eat 可以表示吃饭。','learn-english':'learn 是学，English 是英语；learn English 是学英语。'}[kid],old='先掌握表达材料，再用于独立造句。'))
 for kid,prompt,answer,material in [
  ('want-to-transfer-school','你现在想去学校。请写出“我想去学校”。','I want to go to school.','go-to-school'),
  ('want-to-transfer-eat','你现在想吃饭。请写出“我想吃饭”。','I want to eat.','eat-a-meal')]:
  c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:p,:a,:e,:x)'),dict(k=kid,p=prompt,a=answer,e='独立造句：使用已学结构表达新的意思。',x=answer))
  c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
  c.execute(text("INSERT OR IGNORE INTO course_links VALUES(:k,'want-to-sentence',4,'自编情境表达训练')"),dict(k=kid))
  c.execute(text('INSERT OR IGNORE INTO transfer_materials VALUES(:k,:m)'),dict(k=kid,m=material))
 c.execute(text("INSERT OR IGNORE INTO transfer_materials VALUES('want-to-transfer','learn-english')"))
 materials={
  'every-day':('每天','every day','表示每天，通常可放在这类句子的末尾。'),
  'the-radio':('广播（用于 listen to 后，带冠词）','the radio','listen to the radio＝听广播。to 属于 listen to；the 和 radio 在这里一起使用，不把 to the 当作固定搭配。'),
  'cooking':('做饭（doing 形式）','cooking','cook 是动词原形；cooking 是本课 enjoy / like 后使用的形式。'),
  'cook-at-home':('在家做饭','cook at home','cook＝做饭；at home＝在家。'),
  'this-map':('这张地图','this map','this＝这；map＝地图。'),
  'my-friend':('我的朋友','my friend','my＝我的；friend＝朋友。'),
  'my-teacher':('我的老师','my teacher','my＝我的；teacher＝老师。'),
  'more-time':('更多时间','more time','more＝更多；time＝时间。'),
 }
 for kid,(prompt,answer,explanation) in materials.items():
  c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:p,:a,:e,:x)'),dict(k=kid,p=prompt,a=answer,e=explanation,x=answer))
  c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
 requirements={
  'enjoy-doing-transfer':['cooking'],'decide-to-transfer':['cook-at-home'],
  'like-doing-transfer':['cooking'],'listen-to-transfer':['the-radio','every-day'],
  'look-at-transfer':['this-map'],'wait-for-transfer':['my-friend','every-day'],
  'talk-to-transfer':['my-teacher','every-day'],'ask-for-transfer':['more-time'],
 }
 for target,ids in requirements.items():
  for material in ids:c.execute(text('INSERT OR IGNORE INTO transfer_materials VALUES(:k,:m)'),dict(k=target,m=material))

def missing_material(c,text,kid):
 return c.execute(text('''SELECT k.*,p.* FROM transfer_materials tm JOIN knowledge k ON k.id=tm.material_id
 JOIN progress p ON p.knowledge_id=k.id WHERE tm.knowledge_id=:k AND p.level<3 ORDER BY k.rowid LIMIT 1'''),dict(k=kid)).mappings().first()
