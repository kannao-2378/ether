"""Versioned, original teaching notes; lexical metadata is separate from learner evidence."""
import json
import beginner_notes
from datetime import datetime,timezone
from sqlalchemy import text

BC='https://learnenglish.britishcouncil.org/free-resources/grammar/a1-a2/verbs-followed-ing-or-infinitive'
OX='https://www.oxfordlearnersdictionaries.com/us/definition/english/'
EXTENSION_TRANSLATIONS={'I want to drink water':'我想喝水','drink water':'喝水','drink tea':'喝茶','a glass of water':'一杯水','read books':'读书','enjoy reading':'享受阅读的乐趣','learn English':'学英语','learn to cook':'学习做饭','speak English':'说英语','want water':'想要水','want to drink water':'想喝水','enjoy learning English':'享受学英语的乐趣','want to eat':'想吃饭','eat a meal':'吃一顿饭'}
WORDS={
 'word-i':dict(ipa='/aɪ/',syllables='I',stress='单音节',pos='pron. 人称代词（主格）',definition_en='The person who is speaking.',usage='I 表示“我”，放在本课句子的动作前；无论在句子哪里都大写。',forms=['me（宾格）','my（形容词性物主代词）'],example='I drink water.',zh='我喝水。',error='I 是主语；my 是“我的”，不能写 My drink water 来表示“我喝水”。',extension=['I want to drink water'],source='i_2'),
 'word-drink':dict(ipa='/drɪŋk/',syllables='drink',stress='单音节',pos='v. 动词',definition_en='Take liquid into your mouth and swallow it.',usage='drink + 饮料；本课先练 drink water。',forms=['drinks','drank','drunk','drinking'],example='I drink water.',zh='我喝水。',error='过去式是 drank，过去分词是 drunk。',extension=['drink water','drink tea'],source='drink_1'),
 'word-water':dict(ipa='/ˈwɔːtər/',syllables='wa·ter',stress='第一音节重读',pos='n. 名词；本义不可数',definition_en='The liquid that we drink to stay alive.',usage='表示饮用的水时通常不可数：drink water，不说 a water（本课基础用法）。',forms=[],example='I want water.',zh='我想要水。',error='不要把所有名词都机械地加 a 或复数 s。',extension=['drink water','a glass of water'],source='water_1'),
 'word-read':dict(ipa='/riːd/',syllables='read',stress='单音节',pos='v. 动词',definition_en='Look at written words and understand them.',usage='read + 阅读对象；read books 表示读书这项活动。',forms=['reads','read /red/（过去式、过去分词）','reading'],example='I read books.',zh='我读书。',error='原形 read /riːd/ 和过去式 read /red/ 拼写相同，读音不同。',extension=['read books','enjoy reading'],source='read_1'),
 'word-books':dict(ipa='/bʊks/',syllables='books',stress='单音节',pos='n. 名词复数；原形 book',definition_en='Things with pages that people read.',usage='book 是一本书；books 是复数。本条只训练“书（复数）”这个意思。',forms=['book（单数）','books（复数）'],example='I read books.',zh='我读书。',error='books 的末尾 s 需要保留，读作 /s/。',extension=['read books'],source='book_1'),
 'word-learn':dict(ipa='/lɜːrn/',syllables='learn',stress='单音节',pos='v. 动词',definition_en='Get knowledge or a skill through study or practice.',usage='learn + 学习内容；learn to + 动词原形表示学习做某事。',forms=['learns','learned（美式常用过去式、过去分词）','learning'],example='I learn English.',zh='我学英语。',error='learn English 中 English 前不需要 to。learn to cook 中 to 后接动作。',extension=['learn English','learn to cook'],source='learn'),
 'word-english':dict(ipa='/ˈɪŋɡlɪʃ/',syllables='Eng·lish',stress='第一音节重读',pos='n. 名词（本课：英语）；也可作形容词',definition_en='The language used in countries such as the US and the UK.',usage='语言名称 English 首字母大写；本课练 learn English。',forms=[],example='I learn English.',zh='我学英语。',error='English 的首字母应大写；本系统作为书写提醒，不因此判错。',extension=['learn English','speak English'],source='english_1'),
 'word-want':dict(ipa='/wɑːnt/',syllables='want',stress='单音节',pos='v. 动词',definition_en='Have a wish for something or for doing something.',usage='want + 东西；want to + 动词原形。',forms=['wants','wanted','wanting'],example='I want to drink water.',zh='我想喝水。',error='想要东西用 want water；想做动作才用 want to drink。',extension=['want water','want to drink water'],source='want_1'),
 'word-enjoy':dict(ipa='/ɪnˈdʒɔɪ/',syllables='en·joy',stress='第二音节重读',pos='v. 动词',definition_en='Feel pleasure when doing or experiencing something.',usage='enjoy + 名词；enjoy + doing。',forms=['enjoys','enjoyed','enjoying'],example='I enjoy reading.',zh='我享受阅读的乐趣。',error='不要写 enjoy to read，应写 enjoy reading。',extension=['enjoy reading','enjoy learning English'],source='enjoy',roots='历史上经中古英语、古法语进入英语，含“喜悦”的词义关联；这是词源线索，不能据此推断所有 en- 单词。'),
 'eat-a-meal':dict(ipa='/iːt/',syllables='eat',stress='单音节',pos='v. 动词',definition_en='Take food into your mouth and swallow it.',usage='eat 可以表示吃饭，也可接食物；本条规范答案为 eat。',forms=['eats','ate','eaten','eating'],example='I want to eat.',zh='我想吃饭。',error='eat 的过去式为 ate；本课在 want to 后使用原形 eat。',extension=['want to eat','eat a meal'],source='eat'),
}
STRUCTURES={
 'want-to':('want to + 动词原形','want 表达愿望，to 后接你想做的动作。想要东西则直接 want + 名词。','不要写 want to drinking；正确是 want to drink。'),
 'enjoy-doing':('enjoy + 动词-ing','enjoy 后的动作使用 -ing 形式；它强调从活动中获得乐趣，不表示“想要做”。','不要写 enjoy to read；正确是 enjoy reading。'),
 'decide-to':('decide to + 动词原形','先表达作出决定，再用 to 引出决定做的动作。','不要写 decide doing（本课结构）。'),
 'like-doing':('like + 动词-ing / like to + 动词原形','两种接法都可以；本练习集中训练 doing，不能把 to do 说成语法错误。','按题目要求练 doing；其他自然表达并不因此都是错的。'),
 'listen-to':('listen to + 听的对象','listen 后接听的对象时通常需要 to；to 属于 listen to。','不要漏写 listen to music 中的 to。'),
 'look-at':('look at + 看的对象','at 引出目光指向的对象；look for 表示寻找，含义不同。','看是 look at；寻找是 look for。'),
 'wait-for':('wait for + 等待的对象','for 引出你正在等的人或物。','不要漏写 wait for the bus 中的 for。'),
 'talk-to':('talk to + 交谈对象','to 引出交谈对象；talk with 也可能自然，本课练 talk to。','to 后写交谈对象，不要把 talk to 当成完整句子。'),
 'ask-for':('ask for + 请求的东西','for 后接你希望得到的帮助、时间或物品。','ask someone 是问某人；ask for something 是请求得到某物。'),
}
TRANSLATIONS={'I want to drink water.':'我想喝水。','I enjoy reading.':'我享受阅读的乐趣。','I decide to learn English.':'我决定学习英语。','I like reading books.':'我喜欢读书。','I listen to music every day.':'我每天听音乐。','I listen to music.':'我听音乐。','Please look at this picture.':'请看这张图片。','I look at the picture.':'我看这张图片。','I wait for the bus every day.':'我每天等公共汽车。','I wait for the bus.':'我等公共汽车。','I talk to my friend every day.':'我每天和朋友交谈。','I talk to my friend.':'我和朋友交谈。','I ask for help.':'我请求帮助。','I ask for help when I need it.':'需要时，我会请求帮助。'}
TRANSLATIONS.update({'I decide to study.':'我决定学习。','I like reading.':'我喜欢阅读。','I need to rest.':'我需要休息。','I hope to see you.':'我希望见到你。','I plan to study.':'我计划学习。','I learn to cook.':'我学习做饭。','I try to help.':'我尽力帮忙。','I finish reading.':'我完成阅读。','I practice speaking English.':'我练习说英语。','I keep learning.':'我持续学习。','I think about my future.':'我考虑自己的未来。','I look for my keys.':'我寻找我的钥匙。','I look after my cat.':'我照顾我的猫。','I depend on my family.':'我依靠我的家人。','I agree with you.':'我同意你的看法。','I worry about my dog.':'我担心我的狗。','These keys belong to me.':'这些钥匙属于我。','I pay for lunch.':'我付午饭的钱。','I get up early.':'我早起。','I go home after work.':'我下班后回家。'})
UNITS=[
 ('materials','01 · 先认识动作材料','认清喝水、读书、学英语里的词和短语。',['word-drink','word-water','drink-water','word-read','word-books','read-books','word-learn','word-english','learn-english']),
 ('wishes','02 · 表达我想做什么','区分想要东西与想做动作，练习 I want to。',['word-i','word-want','want-to','want-to-action','want-to-sentence','compose-want-to-drink-water','compose-want-to-read-books','compose-want-to-learn-english']),
 ('enjoyment','03 · 表达喜欢的活动','学 enjoy 后接 doing，替换已学动作。',['word-enjoy','enjoy-doing','drink-water-ing-form','read-books-ing-form','learn-english-ing-form','enjoy-doing-action','enjoy-doing-sentence','compose-enjoy-doing-drink-water','compose-enjoy-doing-read-books','compose-enjoy-doing-learn-english']),
 ('choices','04 · 表达决定与喜好','对比 decide to 与 like doing。',['decide-to','decide-to-action','decide-to-sentence','like-doing','like-doing-action','like-doing-sentence']),
 ('objects','05 · 动作指向谁或什么','练习 listen to、look at、wait for、talk to、ask for。',[p+s for p in ('listen-to','look-at','wait-for','talk-to','ask-for') for s in ('','-action','-sentence')]),
 ('daily','06 · 扩展日常动作','学习需要、计划、寻找、照顾等常用表达。',['need-to','hope-to','plan-to','learn-to','try-to','finish-doing','practice-doing','keep-doing','think-about','look-for','look-after','depend-on','agree-with','worry-about','belong-to','pay-for','get-up','go-home']),
]

def install(c):
 c.execute(text('CREATE TABLE IF NOT EXISTS knowledge_details(knowledge_id TEXT PRIMARY KEY,payload TEXT NOT NULL,version INTEGER NOT NULL,updated_at TEXT NOT NULL)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS learning_courses(id TEXT PRIMARY KEY,title TEXT,goal TEXT,level TEXT)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS course_units(id TEXT PRIMARY KEY,course_id TEXT,title TEXT,goal TEXT,position INTEGER)'))
 c.execute(text('CREATE TABLE IF NOT EXISTS course_items(knowledge_id TEXT PRIMARY KEY,unit_id TEXT,position INTEGER)'))
 for kid in ('word-i','word-want','word-enjoy'):
  w=WORDS[kid];answer='I' if kid=='word-i' else kid[5:];prompt={'I':'我（主格）','want':'想要（动词原形）','enjoy':'享受（动词原形）'}[answer]
  c.execute(text('INSERT OR IGNORE INTO knowledge VALUES(:k,:p,:a,:e,:x)'),dict(k=kid,p=prompt,a=answer,e=w['usage'],x=w['example']))
  c.execute(text('INSERT OR IGNORE INTO progress(knowledge_id) VALUES(:k)'),dict(k=kid))
 c.execute(text("INSERT OR IGNORE INTO learning_courses VALUES('foundation','通用英语 · 基础表达','用已学材料组织自己的基础表达，而不是只记答案。','入门—基础')"))
 position=0
 for index,(unit,title,goal,ids) in enumerate(UNITS):
  c.execute(text('INSERT OR IGNORE INTO course_units VALUES(:u,\'foundation\',:t,:g,:p)'),dict(u=unit,t=title,g=goal,p=index))
  for kid in ids:
   c.execute(text('INSERT OR IGNORE INTO course_items VALUES(:k,:u,:p)'),dict(k=kid,u=unit,p=position));position+=1
 # Idempotent metadata upgrades never rewrite knowledge answers or learner history.
 rows=c.execute(text("SELECT k.*,l.parent_id,COALESCE(l.stage,1) AS stage FROM knowledge k LEFT JOIN course_links l ON l.knowledge_id=k.id WHERE k.id NOT LIKE 'expr-%' AND k.id NOT LIKE 'lex-%' AND k.id NOT LIKE 'sent-%'")).mappings().all()
 for row in rows:
  kid=row['id'];word=WORDS.get(kid);family=kid
  while family not in STRUCTURES:
   parent=c.execute(text('SELECT parent_id FROM course_links WHERE knowledge_id=:k'),dict(k=family)).scalar()
   if not parent:break
   family=parent
  structure=STRUCTURES.get(family)
  is_word=kid.startswith('word-') or kid=='eat-a-meal'
  typ='word' if is_word else 'sentence' if row['stage']>=3 else 'phrase' if row['stage']==2 or kid in ('drink-water','read-books','learn-english','enjoy-reading') or kid.endswith('-form') else 'collocation'
  details=dict(entry_type=typ,level='基础示范',topics=['通用英语','日常表达'],ipa_us=None,syllables=None,stress=None,pos=None,definition_en=None,usage=row['explanation'],structure=None,knowledge_points=[row['explanation']],common_errors=[],forms=[],roots=None,root_note=None,extensions=[],examples=[],sources=[],speech_text=row['answer'],audio_path=None,version=1,review_status='自编教学说明；非官方原版课程')
  if row['example']:
   zh=TRANSLATIONS.get(row['example'])
   if not zh and row['example']==row['answer']:zh=row['prompt']
   details['examples']=[dict(en=row['example'],zh=zh,scene='基础表达示范')]
  if structure:
   details.update(structure=structure[0],usage=structure[1],common_errors=[structure[2]],knowledge_points=[structure[1],row['explanation']])
   if family in ('want-to','enjoy-doing','decide-to','like-doing'):details['sources']=[dict(title='British Council · 动词后接 doing / to do',url=BC)]
   head=WORDS['word-want' if family=='want-to' else 'word-enjoy'] if family in ('want-to','enjoy-doing') else None
   if head:
    details['pronunciation_parts']=[dict(en=family.split('-')[0],ipa=head['ipa'],syllables=head['syllables'],stress=head['stress'])]
    details['extensions']=[dict(en=x,zh=EXTENSION_TRANSLATIONS[x]) for x in head['extension']]
    details['roots']=head.get('roots');details['root_note']='词源说明针对核心动词，不是整句话的词根。' if head.get('roots') else None
    if head.get('roots'):details['sources'].append(dict(title='Oxford · enjoy 词源及用法',url=OX+'enjoy'))
  elif not is_word and row['stage']==1:
   answer=row['answer']
   if answer.endswith(' to') and kid not in ('belong-to',):
    details['structure']=answer+' + 动词原形';details['common_errors']=['本课接具体动作时使用动词原形，不把 doing 直接接在这个 to 后。']
   elif answer.endswith(' doing'):
    details['structure']=answer.replace('doing','动词-ing');details['common_errors']=['本结构后接动作时使用 -ing 形式。注意动作本身的拼写变化。']
   else:
    details['structure']=answer;details['common_errors']=['按完整表达记忆；不要省掉改变含义的介词或副词。']
   if answer.endswith((' to',' doing')) and kid not in ('belong-to',):details['sources']=[dict(title='British Council · 动词结构参考',url=BC)]
  if typ=='sentence':
   details['sentence_parts']=[dict(en='I',zh='主语：谁') ,dict(en=row['answer'][2:].rstrip('.'),zh='表达的动作与其他信息')] if row['answer'].startswith('I ') else []
  if word:
   details.update(ipa_us=word['ipa'],syllables=word['syllables'],stress=word['stress'],pos=word['pos'],definition_en=word['definition_en'],usage=word['usage'],knowledge_points=[word['usage']],common_errors=[word['error']],forms=word['forms'],roots=word.get('roots'),root_note=None if word.get('roots') else '本条不作词根拆解，按完整词形与用法记忆。',examples=[dict(en=word['example'],zh=word['zh'],scene='自编基础例句')],extensions=[dict(en=x,note='相关表达') for x in word['extension']],sources=[dict(title='Oxford · '+row['answer'],url=OX+word['source'])])
  action_examples={'drink-water':('I drink water.','我喝水。'),'read-books':('I read books.','我读书。'),'learn-english':('I learn English.','我学英语。')}
  if kid in action_examples:
   en,zh=action_examples[kid];details['examples']=[dict(en=en,zh=zh,scene='自编基础例句')]
   details['structure']='动词原形 + 动作对象';details['usage']=row['explanation'];details['common_errors']=['短语本身不是带主语的完整句子；前面加入 I 后可以组成基础句子。']
  if word:details['extensions']=[dict(en=x,zh=EXTENSION_TRANSLATIONS[x]) for x in word['extension']]
  beginner_notes.apply(kid,row,details,family)
  details['version']=7
  c.execute(text('INSERT INTO knowledge_details VALUES(:k,:p,7,:t) ON CONFLICT(knowledge_id) DO UPDATE SET payload=excluded.payload,version=excluded.version,updated_at=excluded.updated_at WHERE knowledge_details.version<excluded.version'),dict(k=kid,p=json.dumps(details,ensure_ascii=False),t=datetime.now(timezone.utc).isoformat()))

def details(c,kid):
 raw=c.execute(text('SELECT payload FROM knowledge_details WHERE knowledge_id=:k'),dict(k=kid)).scalar()
 return json.loads(raw) if raw else None

def curriculum(c,include_items=True):
 result=[]
 for course in c.execute(text('SELECT * FROM learning_courses')).mappings():
  units=[]
  for unit in c.execute(text('SELECT * FROM course_units WHERE course_id=:c ORDER BY position'),dict(c=course['id'])).mappings():
   stats=c.execute(text('SELECT COUNT(*) AS total,COALESCE(SUM(p.introduced=1),0) AS introduced,COALESCE(SUM(p.level>=3),0) AS recalled FROM course_items ci JOIN progress p ON p.knowledge_id=ci.knowledge_id WHERE ci.unit_id=:u'),dict(u=unit['id'])).mappings().one()
   item=dict(unit,**stats)
   if include_items:item['items']=[dict(r) for r in c.execute(text('SELECT k.id,k.answer,k.prompt,p.introduced,p.level FROM course_items ci JOIN knowledge k ON k.id=ci.knowledge_id JOIN progress p ON p.knowledge_id=k.id WHERE ci.unit_id=:u ORDER BY ci.position'),dict(u=unit['id'])).mappings()]
   units.append(item)
  result.append(dict(course,units=units,total=sum(u['total'] for u in units)))
 return result
