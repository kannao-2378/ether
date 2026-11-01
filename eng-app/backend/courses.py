"""Original starter content. Not a licensed or frequency-ranked textbook corpus."""
EXTRA=[
 ('need-to','需要做某事','need to','后接动词原形。','I need to rest.'),
 ('hope-to','希望做某事','hope to','后接动词原形。','I hope to see you.'),
 ('plan-to','计划做某事','plan to','后接动词原形。','I plan to study.'),
 ('learn-to','学习做某事','learn to','后接动词原形。','I learn to cook.'),
 ('try-to','努力尝试做某事','try to','try to do 表示努力尝试完成动作。','I try to help.'),
 ('finish-doing','完成做某事（写出 doing 结构）','finish doing','finish 后接 doing。','I finish reading.'),
 ('practice-doing','练习做某事（美式拼写，写出 doing 结构）','practice doing','practice 后接 doing。','I practice speaking English.'),
 ('keep-doing','持续做某事（写出 doing 结构）','keep doing','keep 后接 doing。','I keep learning.'),
 ('think-about','考虑……（使用 about）','think about','后接考虑的对象。','I think about my future.'),
 ('look-for','寻找……','look for','表示寻找，区别于 look at。','I look for my keys.'),
 ('look-after','照顾……（使用 look）','look after','后接照顾的对象。','I look after my cat.'),
 ('depend-on','依靠……（使用 depend）','depend on','后接所依靠的人或事物。','I depend on my family.'),
 ('agree-with','同意某人的看法（使用 agree）','agree with','后接人或观点。','I agree with you.'),
 ('worry-about','担心……','worry about','后接担心的对象。','I worry about my dog.'),
 ('belong-to','属于……','belong to','后接所属的人或集体。','These keys belong to me.'),
 ('pay-for','为……付钱','pay for','后接购买的物品或服务。','I pay for lunch.'),
 ('get-up','起床','get up','常用日常动作短语。','I get up early.'),
 ('go-home','回家','go home','这里 home 前不加 to。','I go home after work.'),
]
PATHS=[
 ('want-to','想喝水','want to drink water','我想喝水。','I want to drink water.','drink water = 喝水；want to 后接 drink。'),
 ('enjoy-doing','享受阅读的乐趣（使用 enjoy）','enjoy reading','我享受阅读的乐趣。','I enjoy reading.','read = 阅读；enjoy 后变为 reading。'),
 ('decide-to','决定学习英语','decide to learn English','我决定学习英语。','I decide to learn English.','learn English = 学习英语；decide to 后接 learn。'),
 ('like-doing','喜欢读书（使用 doing 形式）','like reading books','我喜欢读书（使用 doing 形式）。','I like reading books.','read books = 读书；本题练习 like doing。'),
 ('listen-to','听音乐','listen to music','我每天听音乐。','I listen to music every day.','music = 音乐；every day = 每天。'),
 ('look-at','看这张图片','look at this picture','请看这张图片。','Please look at this picture.','this picture = 这张图片；Please 表示礼貌请求。'),
 ('wait-for','等公共汽车','wait for the bus','我每天等公共汽车。','I wait for the bus every day.','the bus = 公共汽车；wait 后用 for 引出等待对象。'),
 ('talk-to','和我的朋友交谈（使用 to）','talk to my friend','我每天和我的朋友交谈（使用 to）。','I talk to my friend every day.','my friend = 我的朋友；本题使用 talk to。'),
 ('ask-for','请求帮助（使用 ask）','ask for help','我在需要的时候请求帮助。','I ask for help when I need it.','help = 帮助；最后一句包含 when 从句，先使用基础句 I ask for help.。'),
]

def install(c, text):
 c.execute(text('CREATE TABLE IF NOT EXISTS course_links (knowledge_id TEXT PRIMARY KEY,parent_id TEXT,stage INTEGER,source TEXT)'))
 for kid,prompt,answer,explanation,example in EXTRA:
  c.execute(text('INSERT OR IGNORE INTO knowledge VALUES (:k,:p,:a,:e,:x)'),dict(k=kid,p=prompt,a=answer,e=explanation,x=example))
  c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES (:k)'),dict(k=kid))
 for parent,prompt,phrase,sentence_prompt,sentence,explanation in PATHS:
  if parent=='ask-for':sentence_prompt='我请求帮助（使用 ask）。';sentence='I ask for help.';explanation='help = 帮助；ask for help = 请求帮助。'
  for stage,kid,prereq,p,a in [(2,parent+'-action',parent,prompt,phrase),(3,parent+'-sentence',parent+'-action',sentence_prompt,sentence)]:
   c.execute(text('INSERT OR IGNORE INTO knowledge VALUES (:k,:p,:a,:e,:x)'),dict(k=kid,p=p,a=a,e=explanation+(' 主语 I 放在动作前。' if stage==3 and sentence.startswith('I ') else ''),x=sentence))
   c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES (:k)'),dict(k=kid))
   c.execute(text('INSERT OR IGNORE INTO course_links VALUES (:k,:parent,:stage,:source)'),dict(k=kid,parent=prereq,stage=stage,source='自编基础示范课程'))
 transfers=[
  ('want-to','我想学英语。','I want to learn English.','learn English＝学英语。沿用 I want to + 动作，替换原来的 drink water。'),
  ('enjoy-doing','我享受烹饪的乐趣（使用 enjoy）。','I enjoy cooking.','cook＝做饭；enjoy 后接 cooking。'),
  ('decide-to','我决定在家做饭。','I decide to cook at home.','cook at home＝在家做饭；decide to 后接 cook。'),
  ('like-doing','我喜欢做饭（使用 doing 形式）。','I like cooking.','cook＝做饭；本题使用 like doing。'),
  ('listen-to','我每天听广播。','I listen to the radio every day.','the radio＝广播；every day＝每天。'),
  ('look-at','请看这张地图。','Please look at this map.','this map＝这张地图；保留 Please look at。'),
  ('wait-for','我每天等我的朋友。','I wait for my friend every day.','my friend＝我的朋友；等待对象变化，wait for 不变。'),
  ('talk-to','我每天和我的老师交谈（使用 to）。','I talk to my teacher every day.','my teacher＝我的老师；本题沿用 talk to。'),
  ('ask-for','我请求更多时间（使用 ask）。','I ask for more time.','more time＝更多时间；ask for 后接请求的内容。'),
 ]
 for parent,prompt,answer,explanation in transfers:
  kid=parent+'-transfer'
  c.execute(text('INSERT OR IGNORE INTO knowledge VALUES (:k,:p,:a,:e,:x)'),dict(k=kid,p=prompt,a=answer,e='换情境表达：'+explanation,x=answer))
  c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES (:k)'),dict(k=kid))
  c.execute(text('INSERT OR IGNORE INTO course_links VALUES (:k,:p,4,:s)'),dict(k=kid,p=parent+'-sentence',s='自编迁移训练'))
