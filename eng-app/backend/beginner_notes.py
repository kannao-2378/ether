"""Concrete beginner explanations; do not infer grammar from arbitrary word strings."""
MATERIALS = {
 'drink-water': ('drink（喝） + water（水）', 'drink water 就是“喝水”：先说喝，再说喝什么。', [('drink','喝'),('water','水')]),
 'read-books': ('read（读） + books（书）', 'read books 就是“读书”：先说读，再说读什么。', [('read','读'),('books','书，不止一本')]),
 'learn-english': ('learn（学） + English（英语）', 'learn English 就是“学英语”：先说学，再说学什么。', [('learn','学'),('English','英语')]),
 'go-to-school': ('go to school 连起来表示“去学校”。', 'go 是“去”，school 是“学校”。这里中间要有 to，不能写成 go school。', [('go','去'),('to','这里用来连接“去”和地点'),('school','学校')]),
 'enjoy-reading': ('enjoy reading 表示“享受阅读的乐趣”。', 'read 是“阅读”。放在 enjoy 后面时，这里要写成 reading；不要写 enjoy read 或 enjoy to read。', [('enjoy','享受……的乐趣'),('reading','阅读，在这里使用的写法')]),
}
FAMILIES = {
 'want-to': ('先说 want to，再说想做什么。', 'want to 表示“想要做……”。例如想喝水：want to drink water。drink 写基本样子，不改成 drinking。想要水这个东西，则说 want water。'),
 'enjoy-doing': ('先说 enjoy，再把后面的动作改成 -ing 的写法。', 'enjoy 表示“享受……的乐趣”。read 是阅读，接在 enjoy 后要写 reading：enjoy reading＝享受阅读的乐趣。这里的 doing 是写法示意，不是每次都写 do 这个词。'),
 'decide-to': ('先说 decide to，再说决定做什么。', 'decide to 表示“决定做……”。例如 decide to study＝决定学习。study 保持基本写法，不加 -ing。'),
 'like-doing': ('like 后面接喜欢做的活动。', 'like reading＝喜欢阅读。这里把 read 改成 reading。like to read 也可以；本题练习 reading 这种写法。'),
 'listen-to': ('先说 listen to，再说听什么。', 'listen to music＝听音乐。music 是音乐；这里 to 要和 listen 一起保留，不能写 listen music。'),
 'look-at': ('先说 look at，再说看什么。', 'look at the picture＝看这张图片。the picture 是这张图片；这里不要漏掉 at。look for 是寻找，意思不同。'),
 'wait-for': ('先说 wait for，再说等谁或什么。', 'wait for the bus＝等公共汽车。the bus 是公共汽车；这里不要漏掉 for。'),
 'talk-to': ('先说 talk to，再说和谁交谈。', 'talk to my friend＝和我的朋友交谈。my friend 是我的朋友。talk with 也可以；本题练习 talk to。'),
 'ask-for': ('先说 ask for，再说想请求得到什么。', 'ask for help＝请求帮助。help 是帮助；这里不要漏掉 for。'),
}
WORD_NOTES = {
 'word-drink': 'drink 是“喝”。后面放喝的东西：drink water＝喝水，drink tea＝喝茶。drink 是基本写法；drinks、drank、drunk、drinking 是它在不同用法里的其他写法，不必现在一起默写。',
 'word-water': 'water 是“水”。喝水是 drink water。这里不能直接用 a water 表示“一份水”；一杯水可以说 a glass of water。先记住本课的 drink water。',
 'word-read': 'read 是“阅读”。后面接读的东西：read books＝读书。说“我读书”时，在前面加 I（我）：I read books。',
 'word-learn': 'learn 是“学”。learn English＝学英语。说“学习做饭”时用 learn to cook，其中 cook 是做饭。',
 'word-want': 'want 是“想要”。想要水：want water。想喝水：want to drink water。想做一个动作时，这里要用 want to。',
 'word-enjoy': 'enjoy 是“享受……的乐趣”。read 是阅读，但在这里要写 enjoy reading。不是 enjoy read，也不是 enjoy to read。',
 'word-i': 'I 就是“我”。说“我喝水”，按 I（我）→ drink（喝）→ water（水）的顺序写：I drink water。表示“我”的 I 要大写。',
 'word-books': 'book 是一本书，books 表示不止一本书。read books＝读书。本题要写 books，末尾的 s 不能漏。',
 'word-english': 'English 是“英语”。learn English＝学英语。English 的 E 通常大写；本系统会提醒大小写，不因此把答案判错。',
 'eat-a-meal': 'eat 可以表示“吃饭”，也能在后面接吃的食物。“我想吃饭”可以说 I want to eat。',
}
WORKFLOW = ('先掌握表达材料，再用于独立造句。','独立造句：使用已学结构表达新的意思。')

# Reviewed teaching examples, separate from exercises and their prerequisites.
APPLICATIONS = {
 'drink-water': ('说喝水这件事，还没有说是谁喝。', [('drink water','喝水'),('I drink water.','我喝水。')]),
 'read-books': ('说读书这件事，还没有说是谁读。', [('read books','读书'),('I read books.','我读书。')]),
 'learn-english': ('说学英语这件事，还没有说是谁学。', [('learn English','学英语'),('I learn English.','我学英语。')]),
 'go-to-school': ('说去学校这件事。', [('go to school','去学校'),('I want to go to school.','我想去学校。')]),
 'enjoy-reading': ('表达阅读让你感到愉快，不只是想去阅读。', [('enjoy reading','享受阅读的乐趣'),('I enjoy reading.','我享受阅读的乐趣。')]),
 'want-to': ('告诉别人你想做什么；不代表你已经做了。', [('I want to drink water.','我想喝水。'),('I want to learn English.','我想学英语。')]),
 'enjoy-doing': ('表达做这件事让你感到愉快。', [('I enjoy reading.','我享受阅读的乐趣。'),('I enjoy learning English.','我享受学英语的乐趣。')]),
 'decide-to': ('表达已经作出的决定，比只是“想做”更明确。', [('I decide to study.','我决定学习。'),('I decide to learn English.','我决定学英语。')]),
 'like-doing': ('说自己喜欢做的活动。', [('I like reading.','我喜欢阅读。'),('I like learning English.','我喜欢学英语。')]),
 'listen-to': ('说有意识地听什么；不是声音自己传进耳朵。', [('listen to music','听音乐'),('I listen to music.','我听音乐。')]),
 'look-at': ('让目光朝向某个人或东西。', [('look at the picture','看这张图片'),('I look at the picture.','我看这张图片。')]),
 'wait-for': ('人或东西还没到，你在等。', [('wait for the bus','等公共汽车'),('I wait for my friend.','我等我的朋友。')]),
 'talk-to': ('表达和谁说话、交谈。', [('talk to my friend','和我的朋友交谈'),('I talk to my teacher.','我和我的老师交谈。')]),
 'ask-for': ('向别人请求得到东西或帮助。', [('ask for help','请求帮助'),('I ask for more time.','我请求得到更多时间。')]),
}
CHUNKS = [('want to','想要做'),('enjoy','享受……的乐趣'),('decide to','决定做'),('like','喜欢'),
          ('listen to','听'),('look at','看'),('wait for','等待'),('talk to','和……交谈'),('ask for','请求得到')]
TAILS = {'drink water':'喝水','learn English':'学英语','read books':'读书','reading':'阅读',
         'learning English':'学英语','reading books':'读书','study':'学习','music':'音乐',
         'the picture':'这张图片','the bus':'公共汽车','my friend':'我的朋友','my teacher':'我的老师',
         'help':'帮助','more time':'更多时间','go to school':'去学校','eat':'吃饭'}

def enrich(kid,row,details,family):
    application=APPLICATIONS.get(kid) or APPLICATIONS.get(family)
    if application and details['entry_type']!='word':
        scene,examples=application
        details['use_when']=scene
        details['variations']=[dict(en=en,zh=zh) for en,zh in examples if en.casefold().rstrip('.')!=row['answer'].casefold().rstrip('.')]
        if kid not in MATERIALS:
            answer=row['answer'].rstrip('.')
            parts=[]
            if answer.startswith('I '):parts.append(dict(en='I',zh='我'));answer=answer[2:]
            for head,meaning in CHUNKS:
                if answer.startswith(head+' '):
                    tail=answer[len(head)+1:]
                    if tail in TAILS:parts.extend([dict(en=head,zh=meaning),dict(en=tail,zh=TAILS[tail])])
                    break
            if len(parts)>1:details['sentence_parts']=parts
            elif details['entry_type']=='sentence':details['sentence_parts']=[]

def apply(kid, row, details, family):
    """Keep terminology as optional reference; teach concrete meaning first."""
    old = dict(structure=details.get('structure'), usage=details.get('usage'), points=[p for p in details.get('knowledge_points', []) if p not in WORKFLOW])
    if kid in MATERIALS:
        pattern, usage, parts = MATERIALS[kid]
        details.update(structure=pattern, usage=usage, sentence_parts=[dict(en=en,zh=zh) for en,zh in parts],
                       common_errors=['这里只说了做什么；如果要说“我'+row['prompt']+'”，可以在前面加 I（我）。'] if kid in ('drink-water','read-books','learn-english') else details['common_errors'])
    elif kid in WORD_NOTES:
        details.update(structure=None, usage=WORD_NOTES[kid])
        if kid=='word-drink':details['common_errors']=['本题写 drink；drinks、drank、drunk、drinking 是其他用法里的写法，不是本题答案。']
        if kid=='word-i':details['common_errors']=['I 是“我”，my 是“我的”。“我喝水”要写 I drink water，不能写 My drink water。']
    elif family in FAMILIES:
        details.update(structure=FAMILIES[family][0], usage=FAMILIES[family][1])
        if row['answer'].startswith('I '):
            details['sentence_parts']=[dict(en='I',zh='我'),dict(en=row['answer'][2:].rstrip('.'),zh=row['prompt'].removeprefix('我').rstrip('。'))]
    elif kid.endswith('-ing-form'):
        base={'drink-water-ing-form':'drink water','read-books-ing-form':'read books','learn-english-ing-form':'learn English'}.get(kid)
        if not base:return
        details.update(structure=None,usage=f'{base} 表示“{row["prompt"].split("（")[0]}”。接在 enjoy（享受……的乐趣）后面时，要把第一个词换成这里的 {row["answer"]} 这种写法。')
    elif row['answer'].endswith(' to') and family!='belong-to':
        details.update(structure='先说 '+row['answer']+'，再说具体做什么。',usage=f'{row["answer"]} 表示“{row["prompt"]}”。后面的动作保持基本写法，不加 -ing；可以对照下面的例句看怎么连接。')
    elif row['answer'].endswith(' doing'):
        head=row['answer'].removesuffix(' doing')
        details.update(structure=head+' 后的动作写成 -ing 的样子。',usage=f'{head} 后接动作时，本课使用 -ing 写法，例如 read（阅读）写成 reading。doing 是写法示意，不是要求每次填写 doing。')
    else:return
    details['knowledge_points']=[]
    details['grammar_reference']={k:v for k,v in old.items() if v and v not in WORKFLOW}
    enrich(kid,row,details,family)
    if kid in ('drink-water','read-books','learn-english'):
        # The structure already glosses both words; don't repeat it in three blocks.
        details.pop('use_when',None)
        details.pop('grammar_reference',None)
        details['sentence_parts']=[]
        details['usage']={
            'drink-water':'water 在这里表示水，不加 a，也不加复数 s。',
            'read-books':'这里的 books 泛指书；如果说读某一本书，可以说 read a book。',
            'learn-english':'直接说 learn English，不在这两个词之间加 to。',
        }[kid]
        details['common_errors']=[]
    # A variation must add information, not repeat the example already shown.
    shown={e['en'].casefold().rstrip('.!?') for e in details.get('examples',[])}
    details['variations']=[v for v in details.get('variations',[]) if v['en'].casefold().rstrip('.!?') not in shown]
