def familiarity(item):
 if not item.get('introduced'):return 0,'未学'
 level=item.get('level') or 0
 if level>=5:return 4,'稳固'
 if level>=3:return 3,'熟悉'
 if (item.get('attempts') or 0)>0:return 2,'不稳'
 return 1,'初识'

RULES={
 'want-to':dict(title='want：想要东西与想做动作',points=['want + 东西：I want water.','want to + 动词原形：I want to drink water.','I 是主语；want 是主要动词；drink water 是想做的动作。','此规则只适用于这些 want 用法，不推广到所有动词。'],sources=['https://learnenglish.britishcouncil.org/free-resources/grammar/a1-a2/verbs-followed-ing-or-infinitive']),
 'enjoy-doing':dict(title='enjoy 后如何接动作',points=['enjoy 后接事物或活动：I enjoy music.','后面接动作时，用 doing：I enjoy reading.','learn English → learning English；drink water → drinking water。','不能写 enjoy to read，也不能把 reading 原样接到 want to 后。'],sources=['https://learnenglish.britishcouncil.org/free-resources/grammar/a1-a2/verbs-followed-ing-or-infinitive']),
}
