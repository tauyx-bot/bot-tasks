"""Direct project-to-GBZ 2.1 occupational exposure-limit types."""

from typing import Final

from .models import OELRule


OEL_INDEX: Final[dict[str, OELRule]] = {
    '安妥': OELRule(
        project='安妥',
        limit_types=('PC-TWA',),
    ),
    '氨': OELRule(
        project='氨',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '2-氨基吡啶': OELRule(
        project='2-氨基吡啶',
        limit_types=('PC-TWA',),
    ),
    '氨基磺酸铵': OELRule(
        project='氨基磺酸铵',
        limit_types=('PC-TWA',),
    ),
    '氨基氰': OELRule(
        project='氨基氰',
        limit_types=('PC-TWA',),
    ),
    '奥克托今': OELRule(
        project='奥克托今',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '巴豆醛': OELRule(
        project='巴豆醛',
        limit_types=('MAC',),
    ),
    '丁烯醛': OELRule(
        project='丁烯醛',
        limit_types=('MAC',),
    ),
    '百草枯': OELRule(
        project='百草枯',
        limit_types=('PC-TWA',),
    ),
    '百菌清': OELRule(
        project='百菌清',
        limit_types=('MAC',),
    ),
    '钡及其可溶性化合物': OELRule(
        project='钡及其可溶性化合物',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '倍硫磷': OELRule(
        project='倍硫磷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '苯': OELRule(
        project='苯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '苯胺': OELRule(
        project='苯胺',
        limit_types=('PC-TWA',),
    ),
    '苯基醚': OELRule(
        project='苯基醚',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二苯醚': OELRule(
        project='二苯醚',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '苯醌': OELRule(
        project='苯醌',
        limit_types=('PC-TWA',),
    ),
    '苯硫磷': OELRule(
        project='苯硫磷',
        limit_types=('PC-TWA',),
    ),
    '苯乙烯': OELRule(
        project='苯乙烯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '吡啶': OELRule(
        project='吡啶',
        limit_types=('PC-TWA',),
    ),
    '苄基氯': OELRule(
        project='苄基氯',
        limit_types=('MAC',),
    ),
    '丙酸': OELRule(
        project='丙酸',
        limit_types=('PC-TWA',),
    ),
    '丙酮': OELRule(
        project='丙酮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '丙酮氰醇': OELRule(
        project='丙酮氰醇',
        limit_types=('MAC',),
    ),
    '丙烯醇': OELRule(
        project='丙烯醇',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '丙烯腈': OELRule(
        project='丙烯腈',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '丙烯菊酯': OELRule(
        project='丙烯菊酯',
        limit_types=('PC-TWA',),
    ),
    '丙烯醛': OELRule(
        project='丙烯醛',
        limit_types=('MAC',),
    ),
    '丙烯酸': OELRule(
        project='丙烯酸',
        limit_types=('PC-TWA',),
    ),
    '丙烯酸甲酯': OELRule(
        project='丙烯酸甲酯',
        limit_types=('PC-TWA',),
    ),
    '丙烯酸正丁酯': OELRule(
        project='丙烯酸正丁酯',
        limit_types=('PC-TWA',),
    ),
    '丙烯酰胺': OELRule(
        project='丙烯酰胺',
        limit_types=('PC-TWA',),
    ),
    '草甘膦': OELRule(
        project='草甘膦',
        limit_types=('PC-TWA',),
    ),
    '草酸': OELRule(
        project='草酸',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '抽余油': OELRule(
        project='抽余油',
        limit_types=('PC-TWA',),
    ),
    '重氮甲烷': OELRule(
        project='重氮甲烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '臭氧': OELRule(
        project='臭氧',
        limit_types=('MAC',),
    ),
    'o,o-二甲基-S-(甲基氨基甲酰甲基)二硫代磷酸酯': OELRule(
        project='o,o-二甲基-S-(甲基氨基甲酰甲基)二硫代磷酸酯',
        limit_types=('PC-TWA',),
    ),
    '乐果': OELRule(
        project='乐果',
        limit_types=('PC-TWA',),
    ),
    'O,O-二甲基-(2,2,2-三氯-1-羟基乙基)磷酸酯': OELRule(
        project='O,O-二甲基-(2,2,2-三氯-1-羟基乙基)磷酸酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '敌百虫': OELRule(
        project='敌百虫',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    "N-3,4-二氯苯基-N',N'-二甲基脲": OELRule(
        project="N-3,4-二氯苯基-N',N'-二甲基脲",
        limit_types=('PC-TWA',),
    ),
    '敌草隆': OELRule(
        project='敌草隆',
        limit_types=('PC-TWA',),
    ),
    '2,4-二氯苯氧基乙酸': OELRule(
        project='2,4-二氯苯氧基乙酸',
        limit_types=('PC-TWA',),
    ),
    '2,4-滴': OELRule(
        project='2,4-滴',
        limit_types=('PC-TWA',),
    ),
    '二氯二苯基三氯乙烷': OELRule(
        project='二氯二苯基三氯乙烷',
        limit_types=('PC-TWA',),
    ),
    '滴滴涕': OELRule(
        project='滴滴涕',
        limit_types=('PC-TWA',),
    ),
    'DDT': OELRule(
        project='DDT',
        limit_types=('PC-TWA',),
    ),
    '碲及其化合物': OELRule(
        project='碲及其化合物',
        limit_types=('PC-TWA',),
    ),
    '碲化铋': OELRule(
        project='碲化铋',
        limit_types=('PC-TWA',),
    ),
    '碘': OELRule(
        project='碘',
        limit_types=('MAC',),
    ),
    '碘仿': OELRule(
        project='碘仿',
        limit_types=('PC-TWA',),
    ),
    '碘甲烷': OELRule(
        project='碘甲烷',
        limit_types=('PC-TWA',),
    ),
    '叠氮酸蒸气': OELRule(
        project='叠氮酸蒸气',
        limit_types=('MAC',),
    ),
    '叠氮化钠': OELRule(
        project='叠氮化钠',
        limit_types=('MAC',),
    ),
    '1,3-丁二烯': OELRule(
        project='1,3-丁二烯',
        limit_types=('PC-TWA',),
    ),
    '2-丁氧基乙醇': OELRule(
        project='2-丁氧基乙醇',
        limit_types=('PC-TWA',),
    ),
    '丁烯': OELRule(
        project='丁烯',
        limit_types=('PC-TWA',),
    ),
    '毒死蜱': OELRule(
        project='毒死蜱',
        limit_types=('PC-TWA',),
    ),
    '对苯二甲酸': OELRule(
        project='对苯二甲酸',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '对二氯苯': OELRule(
        project='对二氯苯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '对硫磷': OELRule(
        project='对硫磷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '对特丁基甲苯': OELRule(
        project='对特丁基甲苯',
        limit_types=('PC-TWA',),
    ),
    '对硝基苯胺': OELRule(
        project='对硝基苯胺',
        limit_types=('PC-TWA',),
    ),
    '对硝基氯苯': OELRule(
        project='对硝基氯苯',
        limit_types=('PC-TWA',),
    ),
    '多次甲基多苯基多异氰酸酯': OELRule(
        project='多次甲基多苯基多异氰酸酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二苯胺': OELRule(
        project='二苯胺',
        limit_types=('PC-TWA',),
    ),
    '二苯基甲烷二异氰酸酯': OELRule(
        project='二苯基甲烷二异氰酸酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二丙二醇甲醚': OELRule(
        project='二丙二醇甲醚',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '2-甲氧基甲乙氧基丙醇': OELRule(
        project='2-甲氧基甲乙氧基丙醇',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二丙酮醇': OELRule(
        project='二丙酮醇',
        limit_types=('PC-TWA',),
    ),
    '2-N-二丁氨基乙醇': OELRule(
        project='2-N-二丁氨基乙醇',
        limit_types=('PC-TWA',),
    ),
    '二噁烷': OELRule(
        project='二噁烷',
        limit_types=('PC-TWA',),
    ),
    '二噁英类化合物': OELRule(
        project='二噁英类化合物',
        limit_types=('PC-TWA',),
    ),
    '二氟氯甲烷': OELRule(
        project='二氟氯甲烷',
        limit_types=('PC-TWA',),
    ),
    '二甲胺': OELRule(
        project='二甲胺',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二甲苯': OELRule(
        project='二甲苯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    'N,N-二甲基苯胺': OELRule(
        project='N,N-二甲基苯胺',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '1,3-二甲基丁基乙酸酯': OELRule(
        project='1,3-二甲基丁基乙酸酯',
        limit_types=('PC-TWA',),
    ),
    '仲-乙酸己酯': OELRule(
        project='仲-乙酸己酯',
        limit_types=('PC-TWA',),
    ),
    '二甲基二氯硅烷': OELRule(
        project='二甲基二氯硅烷',
        limit_types=('MAC',),
    ),
    '二甲基甲酰胺': OELRule(
        project='二甲基甲酰胺',
        limit_types=('PC-TWA',),
    ),
    '3,3-二甲基联苯胺': OELRule(
        project='3,3-二甲基联苯胺',
        limit_types=('MAC',),
    ),
    '二甲基乙酰胺': OELRule(
        project='二甲基乙酰胺',
        limit_types=('PC-TWA',),
    ),
    '二甲氧基甲烷': OELRule(
        project='二甲氧基甲烷',
        limit_types=('PC-TWA',),
    ),
    '二聚环戊二烯': OELRule(
        project='二聚环戊二烯',
        limit_types=('PC-TWA',),
    ),
    '二硫化碳': OELRule(
        project='二硫化碳',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '1,1-二氯-1-硝基乙烷': OELRule(
        project='1,1-二氯-1-硝基乙烷',
        limit_types=('PC-TWA',),
    ),
    '1,3-二氯丙醇': OELRule(
        project='1,3-二氯丙醇',
        limit_types=('PC-TWA',),
    ),
    '1,2-二氯丙烷': OELRule(
        project='1,2-二氯丙烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '1,3-二氯丙烯': OELRule(
        project='1,3-二氯丙烯',
        limit_types=('PC-TWA',),
    ),
    '二氯二氟甲烷': OELRule(
        project='二氯二氟甲烷',
        limit_types=('PC-TWA',),
    ),
    '二氯甲烷': OELRule(
        project='二氯甲烷',
        limit_types=('PC-TWA',),
    ),
    '二氯乙炔': OELRule(
        project='二氯乙炔',
        limit_types=('MAC',),
    ),
    '1,2-二氯乙烷': OELRule(
        project='1,2-二氯乙烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '1,2-二氯乙烯': OELRule(
        project='1,2-二氯乙烯',
        limit_types=('PC-TWA',),
    ),
    '二硼烷': OELRule(
        project='二硼烷',
        limit_types=('PC-TWA',),
    ),
    '二缩水甘油醚': OELRule(
        project='二缩水甘油醚',
        limit_types=('PC-TWA',),
    ),
    '二硝基苯': OELRule(
        project='二硝基苯',
        limit_types=('PC-TWA',),
    ),
    '二硝基甲苯': OELRule(
        project='二硝基甲苯',
        limit_types=('PC-TWA',),
    ),
    '4,6-二硝基邻甲酚': OELRule(
        project='4,6-二硝基邻甲酚',
        limit_types=('PC-TWA',),
    ),
    '2,4-二硝基氯苯': OELRule(
        project='2,4-二硝基氯苯',
        limit_types=('PC-TWA',),
    ),
    '氮氧化物': OELRule(
        project='氮氧化物',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '一氧化氮': OELRule(
        project='一氧化氮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二氧化氮': OELRule(
        project='二氧化氮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二氧化硫': OELRule(
        project='二氧化硫',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二氧化氯': OELRule(
        project='二氧化氯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二氧化碳': OELRule(
        project='二氧化碳',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二氧化锡': OELRule(
        project='二氧化锡',
        limit_types=('PC-TWA',),
    ),
    '2-二乙氨基乙醇': OELRule(
        project='2-二乙氨基乙醇',
        limit_types=('PC-TWA',),
    ),
    '二乙烯三胺': OELRule(
        project='二乙烯三胺',
        limit_types=('PC-TWA',),
    ),
    '二乙基甲酮': OELRule(
        project='二乙基甲酮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二乙烯基苯': OELRule(
        project='二乙烯基苯',
        limit_types=('PC-TWA',),
    ),
    '二异丁基甲酮': OELRule(
        project='二异丁基甲酮',
        limit_types=('PC-TWA',),
    ),
    '二异氰酸甲苯酯': OELRule(
        project='二异氰酸甲苯酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '甲苯二异氰酸酯': OELRule(
        project='甲苯二异氰酸酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '甲苯-2,4-二异氰酸酯': OELRule(
        project='甲苯-2,4-二异氰酸酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    'TDI': OELRule(
        project='TDI',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二月桂酸二丁基锡': OELRule(
        project='二月桂酸二丁基锡',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '五氧化二钒烟尘': OELRule(
        project='五氧化二钒烟尘',
        limit_types=('PC-TWA',),
    ),
    '钒铁合金尘': OELRule(
        project='钒铁合金尘',
        limit_types=('PC-TWA',),
    ),
    '酚': OELRule(
        project='酚',
        limit_types=('PC-TWA',),
    ),
    '呋喃': OELRule(
        project='呋喃',
        limit_types=('PC-TWA',),
    ),
    '氟化氢': OELRule(
        project='氟化氢',
        limit_types=('MAC',),
    ),
    '氟及其化合物': OELRule(
        project='氟及其化合物',
        limit_types=('PC-TWA',),
    ),
    '锆及其化合物': OELRule(
        project='锆及其化合物',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '镉及其化合物': OELRule(
        project='镉及其化合物',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '汞-金属汞': OELRule(
        project='汞-金属汞',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '汞-有机汞化合物': OELRule(
        project='汞-有机汞化合物',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '钴及其化合物': OELRule(
        project='钴及其化合物',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '过氧化苯甲酰': OELRule(
        project='过氧化苯甲酰',
        limit_types=('PC-TWA',),
    ),
    '过氧化甲乙酮': OELRule(
        project='过氧化甲乙酮',
        limit_types=('MAC',),
    ),
    '过氧化氢': OELRule(
        project='过氧化氢',
        limit_types=('PC-TWA',),
    ),
    '环己胺': OELRule(
        project='环己胺',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '环己醇': OELRule(
        project='环己醇',
        limit_types=('PC-TWA',),
    ),
    '环己酮': OELRule(
        project='环己酮',
        limit_types=('PC-TWA',),
    ),
    '环己烷': OELRule(
        project='环己烷',
        limit_types=('PC-TWA',),
    ),
    '环三次甲基三硝铵': OELRule(
        project='环三次甲基三硝铵',
        limit_types=('PC-TWA',),
    ),
    '黑索今': OELRule(
        project='黑索今',
        limit_types=('PC-TWA',),
    ),
    '环氧丙烷': OELRule(
        project='环氧丙烷',
        limit_types=('PC-TWA',),
    ),
    '环氧氯丙烷': OELRule(
        project='环氧氯丙烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '环氧乙烷': OELRule(
        project='环氧乙烷',
        limit_types=('PC-TWA',),
    ),
    '黄磷': OELRule(
        project='黄磷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '茴香胺': OELRule(
        project='茴香胺',
        limit_types=('PC-TWA',),
    ),
    '甲氧基苯胺': OELRule(
        project='甲氧基苯胺',
        limit_types=('PC-TWA',),
    ),
    '邻-茴香胺': OELRule(
        project='邻-茴香胺',
        limit_types=('PC-TWA',),
    ),
    '对-茴香胺': OELRule(
        project='对-茴香胺',
        limit_types=('PC-TWA',),
    ),
    '邻-甲氧基苯胺': OELRule(
        project='邻-甲氧基苯胺',
        limit_types=('PC-TWA',),
    ),
    '对-甲氧基苯胺': OELRule(
        project='对-甲氧基苯胺',
        limit_types=('PC-TWA',),
    ),
    '己二醇': OELRule(
        project='己二醇',
        limit_types=('MAC',),
    ),
    '1,6-己二异氰酸酯': OELRule(
        project='1,6-己二异氰酸酯',
        limit_types=('PC-TWA',),
    ),
    '己内酰胺': OELRule(
        project='己内酰胺',
        limit_types=('PC-TWA',),
    ),
    '2-己酮': OELRule(
        project='2-己酮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '甲基正丁基甲酮': OELRule(
        project='甲基正丁基甲酮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '甲胺': OELRule(
        project='甲胺',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '甲拌磷': OELRule(
        project='甲拌磷',
        limit_types=('MAC',),
    ),
    '甲苯': OELRule(
        project='甲苯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    'N-甲苯胺O-甲苯胺': OELRule(
        project='N-甲苯胺O-甲苯胺',
        limit_types=('PC-TWA',),
    ),
    '甲醇': OELRule(
        project='甲醇',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '甲酚': OELRule(
        project='甲酚',
        limit_types=('PC-TWA',),
    ),
    '甲基丙烯腈': OELRule(
        project='甲基丙烯腈',
        limit_types=('PC-TWA',),
    ),
    '甲基丙烯酸': OELRule(
        project='甲基丙烯酸',
        limit_types=('PC-TWA',),
    ),
    '甲基丙烯酸甲酯': OELRule(
        project='甲基丙烯酸甲酯',
        limit_types=('PC-TWA',),
    ),
    '甲基丙烯酸缩水甘油酯': OELRule(
        project='甲基丙烯酸缩水甘油酯',
        limit_types=('MAC',),
    ),
    '甲基肼': OELRule(
        project='甲基肼',
        limit_types=('MAC',),
    ),
    '甲基内吸磷': OELRule(
        project='甲基内吸磷',
        limit_types=('PC-TWA',),
    ),
    '18-甲基炔诺酮': OELRule(
        project='18-甲基炔诺酮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '炔诺孕酮': OELRule(
        project='炔诺孕酮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '甲基叔丁基醚': OELRule(
        project='甲基叔丁基醚',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '甲硫醇': OELRule(
        project='甲硫醇',
        limit_types=('PC-TWA',),
    ),
    '甲醛': OELRule(
        project='甲醛',
        limit_types=('MAC',),
    ),
    '甲酸': OELRule(
        project='甲酸',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '甲乙酮': OELRule(
        project='甲乙酮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '2-丁酮': OELRule(
        project='2-丁酮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '丁酮': OELRule(
        project='丁酮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '2-甲氧基乙醇': OELRule(
        project='2-甲氧基乙醇',
        limit_types=('PC-TWA',),
    ),
    '2-甲氧基乙基乙酸酯': OELRule(
        project='2-甲氧基乙基乙酸酯',
        limit_types=('PC-TWA',),
    ),
    '甲氧氯': OELRule(
        project='甲氧氯',
        limit_types=('PC-TWA',),
    ),
    '间苯二酚': OELRule(
        project='间苯二酚',
        limit_types=('PC-TWA',),
    ),
    '焦炉逸散物': OELRule(
        project='焦炉逸散物',
        limit_types=('PC-TWA',),
    ),
    '肼': OELRule(
        project='肼',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '久效磷': OELRule(
        project='久效磷',
        limit_types=('PC-TWA',),
    ),
    '糠醇': OELRule(
        project='糠醇',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '糠醛': OELRule(
        project='糠醛',
        limit_types=('PC-TWA',),
    ),
    '考的松': OELRule(
        project='考的松',
        limit_types=('PC-TWA',),
    ),
    '苦味酸': OELRule(
        project='苦味酸',
        limit_types=('PC-TWA',),
    ),
    '2,4,6-三硝基苯酚': OELRule(
        project='2,4,6-三硝基苯酚',
        limit_types=('PC-TWA',),
    ),
    '癸硼烷': OELRule(
        project='癸硼烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '联苯': OELRule(
        project='联苯',
        limit_types=('PC-TWA',),
    ),
    '邻苯二甲酸二丁酯': OELRule(
        project='邻苯二甲酸二丁酯',
        limit_types=('PC-TWA',),
    ),
    '邻苯二甲酸酐': OELRule(
        project='邻苯二甲酸酐',
        limit_types=('MAC',),
    ),
    '邻二氯苯': OELRule(
        project='邻二氯苯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '邻氯苯乙烯': OELRule(
        project='邻氯苯乙烯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '邻氯苄叉丙二腈': OELRule(
        project='邻氯苄叉丙二腈',
        limit_types=('MAC',),
    ),
    '邻仲丁基苯酚': OELRule(
        project='邻仲丁基苯酚',
        limit_types=('PC-TWA',),
    ),
    '磷胺': OELRule(
        project='磷胺',
        limit_types=('PC-TWA',),
    ),
    '磷化氢': OELRule(
        project='磷化氢',
        limit_types=('MAC',),
    ),
    '磷酸': OELRule(
        project='磷酸',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '磷酸二丁基苯酯': OELRule(
        project='磷酸二丁基苯酯',
        limit_types=('PC-TWA',),
    ),
    '硫化氢': OELRule(
        project='硫化氢',
        limit_types=('MAC',),
    ),
    '硫酸钡': OELRule(
        project='硫酸钡',
        limit_types=('PC-TWA',),
    ),
    '硫酸二甲酯': OELRule(
        project='硫酸二甲酯',
        limit_types=('PC-TWA',),
    ),
    '硫酸及三氧化硫': OELRule(
        project='硫酸及三氧化硫',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '硫酰氟': OELRule(
        project='硫酰氟',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '六氟丙酮': OELRule(
        project='六氟丙酮',
        limit_types=('PC-TWA',),
    ),
    '六氟丙烯': OELRule(
        project='六氟丙烯',
        limit_types=('PC-TWA',),
    ),
    '六氟化硫': OELRule(
        project='六氟化硫',
        limit_types=('PC-TWA',),
    ),
    '六六六': OELRule(
        project='六六六',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '六氯环己烷': OELRule(
        project='六氯环己烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    'γ-六六六': OELRule(
        project='γ-六六六',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '六六六氯环己烷': OELRule(
        project='六六六氯环己烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '六氯丁二烯': OELRule(
        project='六氯丁二烯',
        limit_types=('PC-TWA',),
    ),
    '六氯环戊二烯': OELRule(
        project='六氯环戊二烯',
        limit_types=('PC-TWA',),
    ),
    '六氯萘': OELRule(
        project='六氯萘',
        limit_types=('PC-TWA',),
    ),
    '六氯乙烷': OELRule(
        project='六氯乙烷',
        limit_types=('PC-TWA',),
    ),
    '氯': OELRule(
        project='氯',
        limit_types=('MAC',),
    ),
    '氯苯': OELRule(
        project='氯苯',
        limit_types=('PC-TWA',),
    ),
    '氯丙酮': OELRule(
        project='氯丙酮',
        limit_types=('MAC',),
    ),
    '氯丙烯': OELRule(
        project='氯丙烯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    'β-氯丁二烯': OELRule(
        project='β-氯丁二烯',
        limit_types=('PC-TWA',),
    ),
    '氯化铵烟': OELRule(
        project='氯化铵烟',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '氯化汞': OELRule(
        project='氯化汞',
        limit_types=('PC-TWA',),
    ),
    '升汞': OELRule(
        project='升汞',
        limit_types=('PC-TWA',),
    ),
    '氯化苦': OELRule(
        project='氯化苦',
        limit_types=('MAC',),
    ),
    '氯化氢及盐酸': OELRule(
        project='氯化氢及盐酸',
        limit_types=('MAC',),
    ),
    '氯化氰': OELRule(
        project='氯化氰',
        limit_types=('MAC',),
    ),
    '氯化锌烟': OELRule(
        project='氯化锌烟',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '氯甲甲醚': OELRule(
        project='氯甲甲醚',
        limit_types=('MAC',),
    ),
    '氯甲烷': OELRule(
        project='氯甲烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '氯联苯': OELRule(
        project='氯联苯',
        limit_types=('PC-TWA',),
    ),
    '氯萘': OELRule(
        project='氯萘',
        limit_types=('PC-TWA',),
    ),
    '氯乙醇': OELRule(
        project='氯乙醇',
        limit_types=('MAC',),
    ),
    '氯乙醛': OELRule(
        project='氯乙醛',
        limit_types=('MAC',),
    ),
    '氯乙酸': OELRule(
        project='氯乙酸',
        limit_types=('MAC',),
    ),
    '氯乙烯': OELRule(
        project='氯乙烯',
        limit_types=('PC-TWA',),
    ),
    'α-氯乙酰苯': OELRule(
        project='α-氯乙酰苯',
        limit_types=('PC-TWA',),
    ),
    '氯乙酰氯': OELRule(
        project='氯乙酰氯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '马拉硫磷': OELRule(
        project='马拉硫磷',
        limit_types=('PC-TWA',),
    ),
    '马来酸酐': OELRule(
        project='马来酸酐',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '吗啉': OELRule(
        project='吗啉',
        limit_types=('PC-TWA',),
    ),
    '煤焦油沥青挥发物': OELRule(
        project='煤焦油沥青挥发物',
        limit_types=('PC-TWA',),
    ),
    '锰及其无机化合物': OELRule(
        project='锰及其无机化合物',
        limit_types=('PC-TWA',),
    ),
    '钼,不溶性化合物': OELRule(
        project='钼,不溶性化合物',
        limit_types=('PC-TWA',),
    ),
    '钼,可溶性化合物': OELRule(
        project='钼,可溶性化合物',
        limit_types=('PC-TWA',),
    ),
    '内吸磷': OELRule(
        project='内吸磷',
        limit_types=('PC-TWA',),
    ),
    '萘': OELRule(
        project='萘',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '2-萘酚': OELRule(
        project='2-萘酚',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '萘烷': OELRule(
        project='萘烷',
        limit_types=('PC-TWA',),
    ),
    '尿素': OELRule(
        project='尿素',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '金属镍与难溶性镍化合物': OELRule(
        project='金属镍与难溶性镍化合物',
        limit_types=('PC-TWA',),
    ),
    '可溶性镍化合物': OELRule(
        project='可溶性镍化合物',
        limit_types=('PC-TWA',),
    ),
    '铍及其化合物': OELRule(
        project='铍及其化合物',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '偏二甲基肼': OELRule(
        project='偏二甲基肼',
        limit_types=('PC-TWA',),
    ),
    '铅尘': OELRule(
        project='铅尘',
        limit_types=('PC-TWA',),
    ),
    '铅烟': OELRule(
        project='铅烟',
        limit_types=('PC-TWA',),
    ),
    '氢化锂': OELRule(
        project='氢化锂',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '氢醌': OELRule(
        project='氢醌',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '氢氧化钾': OELRule(
        project='氢氧化钾',
        limit_types=('MAC',),
    ),
    '氢氧化钠': OELRule(
        project='氢氧化钠',
        limit_types=('MAC',),
    ),
    '氢氧化铯': OELRule(
        project='氢氧化铯',
        limit_types=('PC-TWA',),
    ),
    '氰氨化钙': OELRule(
        project='氰氨化钙',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '氰化氢': OELRule(
        project='氰化氢',
        limit_types=('MAC',),
    ),
    '氰化物': OELRule(
        project='氰化物',
        limit_types=('MAC',),
    ),
    '氰戊菊酯': OELRule(
        project='氰戊菊酯',
        limit_types=('PC-TWA',),
    ),
    '全氟异丁烯': OELRule(
        project='全氟异丁烯',
        limit_types=('MAC',),
    ),
    '壬烷': OELRule(
        project='壬烷',
        limit_types=('PC-TWA',),
    ),
    '溶剂汽油': OELRule(
        project='溶剂汽油',
        limit_types=('PC-TWA',),
    ),
    '乳酸正丁酯': OELRule(
        project='乳酸正丁酯',
        limit_types=('PC-TWA',),
    ),
    '三氟化氯': OELRule(
        project='三氟化氯',
        limit_types=('MAC',),
    ),
    '三氟化硼': OELRule(
        project='三氟化硼',
        limit_types=('MAC',),
    ),
    '三氟甲基次氟化物': OELRule(
        project='三氟甲基次氟化物',
        limit_types=('MAC',),
    ),
    '三甲苯磷酸酯': OELRule(
        project='三甲苯磷酸酯',
        limit_types=('PC-TWA',),
    ),
    '1,2,3-三氯丙烷': OELRule(
        project='1,2,3-三氯丙烷',
        limit_types=('PC-TWA',),
    ),
    '三氯化磷': OELRule(
        project='三氯化磷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '三氯甲烷': OELRule(
        project='三氯甲烷',
        limit_types=('PC-TWA',),
    ),
    '氯仿': OELRule(
        project='氯仿',
        limit_types=('PC-TWA',),
    ),
    '三氯硫磷': OELRule(
        project='三氯硫磷',
        limit_types=('MAC',),
    ),
    '三氯氢硅': OELRule(
        project='三氯氢硅',
        limit_types=('MAC',),
    ),
    '三氯氧磷': OELRule(
        project='三氯氧磷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '三氯乙醛': OELRule(
        project='三氯乙醛',
        limit_types=('MAC',),
    ),
    '1,1,1-三氯乙烷': OELRule(
        project='1,1,1-三氯乙烷',
        limit_types=('PC-TWA',),
    ),
    '三氯乙烯': OELRule(
        project='三氯乙烯',
        limit_types=('PC-TWA',),
    ),
    '三硝基甲苯': OELRule(
        project='三硝基甲苯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '三溴甲烷': OELRule(
        project='三溴甲烷',
        limit_types=('PC-TWA',),
    ),
    '三氧化铬、铬酸盐、重铬酸盐': OELRule(
        project='三氧化铬、铬酸盐、重铬酸盐',
        limit_types=('PC-TWA',),
    ),
    '三氧化铬': OELRule(
        project='三氧化铬',
        limit_types=('PC-TWA',),
    ),
    '铬酸盐': OELRule(
        project='铬酸盐',
        limit_types=('PC-TWA',),
    ),
    '重铬酸盐': OELRule(
        project='重铬酸盐',
        limit_types=('PC-TWA',),
    ),
    '三乙基氯化锡': OELRule(
        project='三乙基氯化锡',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '杀螟松': OELRule(
        project='杀螟松',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '杀鼠灵': OELRule(
        project='杀鼠灵',
        limit_types=('PC-TWA',),
    ),
    '3-(1-丙酮基苄基)-4-羟基香豆素': OELRule(
        project='3-(1-丙酮基苄基)-4-羟基香豆素',
        limit_types=('PC-TWA',),
    ),
    '砷化氢': OELRule(
        project='砷化氢',
        limit_types=('MAC',),
    ),
    '砷及其无机化合物': OELRule(
        project='砷及其无机化合物',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '石蜡烟': OELRule(
        project='石蜡烟',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '十溴联苯醚': OELRule(
        project='十溴联苯醚',
        limit_types=('PC-TWA',),
    ),
    '石油沥青烟': OELRule(
        project='石油沥青烟',
        limit_types=('PC-TWA',),
    ),
    '双(巯基乙酸)二辛基锡': OELRule(
        project='双(巯基乙酸)二辛基锡',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '双酚A': OELRule(
        project='双酚A',
        limit_types=('PC-TWA',),
    ),
    '双硫醒': OELRule(
        project='双硫醒',
        limit_types=('PC-TWA',),
    ),
    '双氯甲醚': OELRule(
        project='双氯甲醚',
        limit_types=('MAC',),
    ),
    '四氯化碳': OELRule(
        project='四氯化碳',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '四氯乙烯': OELRule(
        project='四氯乙烯',
        limit_types=('PC-TWA',),
    ),
    '四氢呋喃': OELRule(
        project='四氢呋喃',
        limit_types=('PC-TWA',),
    ),
    '四氢化硅': OELRule(
        project='四氢化硅',
        limit_types=('PC-TWA',),
    ),
    '四氢化锗': OELRule(
        project='四氢化锗',
        limit_types=('PC-TWA',),
    ),
    '四溴化碳': OELRule(
        project='四溴化碳',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '四乙基铅': OELRule(
        project='四乙基铅',
        limit_types=('PC-TWA',),
    ),
    '松节油': OELRule(
        project='松节油',
        limit_types=('PC-TWA',),
    ),
    '铊及其可溶性化合物': OELRule(
        project='铊及其可溶性化合物',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '钽及其氧化物': OELRule(
        project='钽及其氧化物',
        limit_types=('PC-TWA',),
    ),
    '碳酸钠': OELRule(
        project='碳酸钠',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '碳酰氯': OELRule(
        project='碳酰氯',
        limit_types=('MAC',),
    ),
    '光气': OELRule(
        project='光气',
        limit_types=('MAC',),
    ),
    '羰基氟': OELRule(
        project='羰基氟',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '羰基镍': OELRule(
        project='羰基镍',
        limit_types=('MAC',),
    ),
    '锑及其化合物': OELRule(
        project='锑及其化合物',
        limit_types=('PC-TWA',),
    ),
    '铜尘': OELRule(
        project='铜尘',
        limit_types=('PC-TWA',),
    ),
    '铜烟': OELRule(
        project='铜烟',
        limit_types=('PC-TWA',),
    ),
    '钨及其不溶性化合物': OELRule(
        project='钨及其不溶性化合物',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '五氟氯乙烷': OELRule(
        project='五氟氯乙烷',
        limit_types=('PC-TWA',),
    ),
    '五硫化二磷': OELRule(
        project='五硫化二磷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '五氯酚及其钠盐': OELRule(
        project='五氯酚及其钠盐',
        limit_types=('PC-TWA',),
    ),
    '五羰基铁': OELRule(
        project='五羰基铁',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '五氧化二磷': OELRule(
        project='五氧化二磷',
        limit_types=('MAC',),
    ),
    '戊醇': OELRule(
        project='戊醇',
        limit_types=('PC-TWA',),
    ),
    '戊烷': OELRule(
        project='戊烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '硒化氢': OELRule(
        project='硒化氢',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '硒及其化合物': OELRule(
        project='硒及其化合物',
        limit_types=('PC-TWA',),
    ),
    '纤维素': OELRule(
        project='纤维素',
        limit_types=('PC-TWA',),
    ),
    '硝化甘油': OELRule(
        project='硝化甘油',
        limit_types=('MAC',),
    ),
    '硝基苯': OELRule(
        project='硝基苯',
        limit_types=('PC-TWA',),
    ),
    '1-硝基丙烷': OELRule(
        project='1-硝基丙烷',
        limit_types=('PC-TWA',),
    ),
    '2-硝基丙烷': OELRule(
        project='2-硝基丙烷',
        limit_types=('PC-TWA',),
    ),
    '硝基甲苯': OELRule(
        project='硝基甲苯',
        limit_types=('PC-TWA',),
    ),
    '硝基甲烷': OELRule(
        project='硝基甲烷',
        limit_types=('PC-TWA',),
    ),
    '硝基乙烷': OELRule(
        project='硝基乙烷',
        limit_types=('PC-TWA',),
    ),
    '辛烷': OELRule(
        project='辛烷',
        limit_types=('PC-TWA',),
    ),
    '溴': OELRule(
        project='溴',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '溴化氢': OELRule(
        project='溴化氢',
        limit_types=('MAC',),
    ),
    '1-溴丙烷': OELRule(
        project='1-溴丙烷',
        limit_types=('PC-TWA',),
    ),
    '溴甲烷': OELRule(
        project='溴甲烷',
        limit_types=('PC-TWA',),
    ),
    '溴氰菊酯': OELRule(
        project='溴氰菊酯',
        limit_types=('PC-TWA',),
    ),
    '溴鼠灵': OELRule(
        project='溴鼠灵',
        limit_types=('PC-TWA',),
    ),
    '氧化钙': OELRule(
        project='氧化钙',
        limit_types=('PC-TWA',),
    ),
    '氧化镁烟': OELRule(
        project='氧化镁烟',
        limit_types=('PC-TWA',),
    ),
    '氧化锌': OELRule(
        project='氧化锌',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '氧乐果': OELRule(
        project='氧乐果',
        limit_types=('PC-TWA',),
    ),
    '液化石油气': OELRule(
        project='液化石油气',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '非高原': OELRule(
        project='非高原',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '海拔2000m~3000m': OELRule(
        project='海拔2000m~3000m',
        limit_types=('MAC',),
    ),
    '海拔>3000m': OELRule(
        project='海拔>3000m',
        limit_types=('MAC',),
    ),
    '乙胺': OELRule(
        project='乙胺',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙苯': OELRule(
        project='乙苯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙醇胺': OELRule(
        project='乙醇胺',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙二胺': OELRule(
        project='乙二胺',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙二醇': OELRule(
        project='乙二醇',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙二醇二硝酸酯': OELRule(
        project='乙二醇二硝酸酯',
        limit_types=('PC-TWA',),
    ),
    '乙酐': OELRule(
        project='乙酐',
        limit_types=('PC-TWA',),
    ),
    'N-乙基吗啉': OELRule(
        project='N-乙基吗啉',
        limit_types=('PC-TWA',),
    ),
    '乙基戊基甲酮': OELRule(
        project='乙基戊基甲酮',
        limit_types=('PC-TWA',),
    ),
    '乙腈': OELRule(
        project='乙腈',
        limit_types=('PC-TWA',),
    ),
    '乙硫醇': OELRule(
        project='乙硫醇',
        limit_types=('PC-TWA',),
    ),
    '乙醚': OELRule(
        project='乙醚',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙醛': OELRule(
        project='乙醛',
        limit_types=('MAC',),
    ),
    '乙酸': OELRule(
        project='乙酸',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙酸丙酯': OELRule(
        project='乙酸丙酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙酸丁酯': OELRule(
        project='乙酸丁酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙酸甲酯': OELRule(
        project='乙酸甲酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙酸戊酯': OELRule(
        project='乙酸戊酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙酸乙烯酯': OELRule(
        project='乙酸乙烯酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙酸乙酯': OELRule(
        project='乙酸乙酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙烯酮': OELRule(
        project='乙烯酮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '乙酰甲胺磷': OELRule(
        project='乙酰甲胺磷',
        limit_types=('PC-TWA',),
    ),
    '乙酰水杨酸': OELRule(
        project='乙酰水杨酸',
        limit_types=('PC-TWA',),
    ),
    '阿司匹林': OELRule(
        project='阿司匹林',
        limit_types=('PC-TWA',),
    ),
    '2-乙氧基乙醇': OELRule(
        project='2-乙氧基乙醇',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '2-乙氧基乙基乙酸酯': OELRule(
        project='2-乙氧基乙基乙酸酯',
        limit_types=('PC-TWA',),
    ),
    '钇及其化合物': OELRule(
        project='钇及其化合物',
        limit_types=('PC-TWA',),
    ),
    '异丙胺': OELRule(
        project='异丙胺',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '异丙醇': OELRule(
        project='异丙醇',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    'N-异丙基苯胺': OELRule(
        project='N-异丙基苯胺',
        limit_types=('PC-TWA',),
    ),
    '异稻瘟净': OELRule(
        project='异稻瘟净',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '异佛尔酮': OELRule(
        project='异佛尔酮',
        limit_types=('MAC',),
    ),
    '异佛尔酮二异氰酸酯': OELRule(
        project='异佛尔酮二异氰酸酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '异氰酸甲酯': OELRule(
        project='异氰酸甲酯',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '异亚丙基丙酮': OELRule(
        project='异亚丙基丙酮',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '铟及其化合物': OELRule(
        project='铟及其化合物',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '茚': OELRule(
        project='茚',
        limit_types=('PC-TWA',),
    ),
    '莠去津': OELRule(
        project='莠去津',
        limit_types=('PC-TWA',),
    ),
    '正丙醇': OELRule(
        project='正丙醇',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '正丁胺': OELRule(
        project='正丁胺',
        limit_types=('MAC',),
    ),
    '正丁醇': OELRule(
        project='正丁醇',
        limit_types=('PC-TWA',),
    ),
    '正丁基硫醇': OELRule(
        project='正丁基硫醇',
        limit_types=('PC-TWA',),
    ),
    '正丁基缩水甘油醚': OELRule(
        project='正丁基缩水甘油醚',
        limit_types=('PC-TWA',),
    ),
    '正丁醛': OELRule(
        project='正丁醛',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '正庚烷': OELRule(
        project='正庚烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '正己烷': OELRule(
        project='正己烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '二甲基亚砜': OELRule(
        project='二甲基亚砜',
        limit_types=('PC-TWA',),
    ),
    '对苯二胺': OELRule(
        project='对苯二胺',
        limit_types=('PC-TWA',),
    ),
    '三甲基氯化锡': OELRule(
        project='三甲基氯化锡',
        limit_types=('MAC',),
    ),
    '白云石粉尘': OELRule(
        project='白云石粉尘',
        limit_types=('PC-TWA',),
    ),
    '玻璃钢粉尘': OELRule(
        project='玻璃钢粉尘',
        limit_types=('PC-TWA',),
    ),
    '茶尘': OELRule(
        project='茶尘',
        limit_types=('PC-TWA',),
    ),
    '沉淀SiO2': OELRule(
        project='沉淀SiO2',
        limit_types=('PC-TWA',),
    ),
    '白炭黑': OELRule(
        project='白炭黑',
        limit_types=('PC-TWA',),
    ),
    '白炭黑粉尘': OELRule(
        project='白炭黑粉尘',
        limit_types=('PC-TWA',),
    ),
    '大理石粉尘': OELRule(
        project='大理石粉尘',
        limit_types=('PC-TWA',),
    ),
    '碳酸钙': OELRule(
        project='碳酸钙',
        limit_types=('PC-TWA',),
    ),
    '碳酸钙粉尘': OELRule(
        project='碳酸钙粉尘',
        limit_types=('PC-TWA',),
    ),
    '电焊烟尘': OELRule(
        project='电焊烟尘',
        limit_types=('PC-TWA',),
    ),
    '二氧化钛粉尘': OELRule(
        project='二氧化钛粉尘',
        limit_types=('PC-TWA',),
    ),
    '沸石粉尘': OELRule(
        project='沸石粉尘',
        limit_types=('PC-TWA',),
    ),
    '酚醛树酯粉尘': OELRule(
        project='酚醛树酯粉尘',
        limit_types=('PC-TWA',),
    ),
    '工业酶混合尘': OELRule(
        project='工业酶混合尘',
        limit_types=('PC-TWA',),
    ),
    '谷物粉尘': OELRule(
        project='谷物粉尘',
        limit_types=('PC-TWA',),
    ),
    '硅灰石粉尘': OELRule(
        project='硅灰石粉尘',
        limit_types=('PC-TWA',),
    ),
    '硅藻土粉尘': OELRule(
        project='硅藻土粉尘',
        limit_types=('PC-TWA',),
    ),
    '过氯酸铵粉尘': OELRule(
        project='过氯酸铵粉尘',
        limit_types=('PC-TWA',),
    ),
    '滑石粉尘': OELRule(
        project='滑石粉尘',
        limit_types=('PC-TWA',),
    ),
    '活性炭粉尘': OELRule(
        project='活性炭粉尘',
        limit_types=('PC-TWA',),
    ),
    '聚丙烯粉尘': OELRule(
        project='聚丙烯粉尘',
        limit_types=('PC-TWA',),
    ),
    '聚丙烯腈纤维粉尘': OELRule(
        project='聚丙烯腈纤维粉尘',
        limit_types=('PC-TWA',),
    ),
    '聚氯乙烯粉尘': OELRule(
        project='聚氯乙烯粉尘',
        limit_types=('PC-TWA',),
    ),
    '聚乙烯粉尘': OELRule(
        project='聚乙烯粉尘',
        limit_types=('PC-TWA',),
    ),
    '铝金属、铝合金粉尘': OELRule(
        project='铝金属、铝合金粉尘',
        limit_types=('PC-TWA',),
    ),
    '铝金属粉尘': OELRule(
        project='铝金属粉尘',
        limit_types=('PC-TWA',),
    ),
    '铝合金粉尘': OELRule(
        project='铝合金粉尘',
        limit_types=('PC-TWA',),
    ),
    '氧化铝粉尘': OELRule(
        project='氧化铝粉尘',
        limit_types=('PC-TWA',),
    ),
    '亚麻': OELRule(
        project='亚麻',
        limit_types=('PC-TWA',),
    ),
    '黄麻': OELRule(
        project='黄麻',
        limit_types=('PC-TWA',),
    ),
    '苎麻': OELRule(
        project='苎麻',
        limit_types=('PC-TWA',),
    ),
    '煤尘': OELRule(
        project='煤尘',
        limit_types=('PC-TWA',),
    ),
    '棉尘': OELRule(
        project='棉尘',
        limit_types=('PC-TWA',),
    ),
    '木粉尘': OELRule(
        project='木粉尘',
        limit_types=('PC-TWA',),
    ),
    '凝聚SiO2粉尘': OELRule(
        project='凝聚SiO2粉尘',
        limit_types=('PC-TWA',),
    ),
    '膨润土粉尘': OELRule(
        project='膨润土粉尘',
        limit_types=('PC-TWA',),
    ),
    '皮毛粉尘': OELRule(
        project='皮毛粉尘',
        limit_types=('PC-TWA',),
    ),
    '人造矿物纤维绝热棉粉尘': OELRule(
        project='人造矿物纤维绝热棉粉尘',
        limit_types=('PC-TWA',),
    ),
    '玻璃棉粉尘': OELRule(
        project='玻璃棉粉尘',
        limit_types=('PC-TWA',),
    ),
    '矿渣棉粉尘': OELRule(
        project='矿渣棉粉尘',
        limit_types=('PC-TWA',),
    ),
    '岩棉粉尘': OELRule(
        project='岩棉粉尘',
        limit_types=('PC-TWA',),
    ),
    '桑蚕丝尘': OELRule(
        project='桑蚕丝尘',
        limit_types=('PC-TWA',),
    ),
    '砂轮磨尘': OELRule(
        project='砂轮磨尘',
        limit_types=('PC-TWA',),
    ),
    '石膏粉尘': OELRule(
        project='石膏粉尘',
        limit_types=('PC-TWA',),
    ),
    '石灰石粉尘': OELRule(
        project='石灰石粉尘',
        limit_types=('PC-TWA',),
    ),
    '石棉粉尘纤维': OELRule(
        project='石棉粉尘纤维',
        limit_types=('PC-TWA',),
    ),
    '石墨粉尘': OELRule(
        project='石墨粉尘',
        limit_types=('PC-TWA',),
    ),
    '水泥粉尘': OELRule(
        project='水泥粉尘',
        limit_types=('PC-TWA',),
    ),
    '炭黑粉尘': OELRule(
        project='炭黑粉尘',
        limit_types=('PC-TWA',),
    ),
    '碳化硅粉尘': OELRule(
        project='碳化硅粉尘',
        limit_types=('PC-TWA',),
    ),
    '碳纤维粉尘': OELRule(
        project='碳纤维粉尘',
        limit_types=('PC-TWA',),
    ),
    '矽尘10%≤游离SiO2含量≤50%50%<游离SiO2含量≤80%游离SiO2含量>80%': OELRule(
        project='矽尘10%≤游离SiO2含量≤50%50%<游离SiO2含量≤80%游离SiO2含量>80%',
        limit_types=('PC-TWA',),
    ),
    '稀土粉尘': OELRule(
        project='稀土粉尘',
        limit_types=('PC-TWA',),
    ),
    '洗衣粉混合尘': OELRule(
        project='洗衣粉混合尘',
        limit_types=('PC-TWA',),
    ),
    '烟草尘': OELRule(
        project='烟草尘',
        limit_types=('PC-TWA',),
    ),
    '萤石混合性粉尘': OELRule(
        project='萤石混合性粉尘',
        limit_types=('PC-TWA',),
    ),
    '云母粉尘': OELRule(
        project='云母粉尘',
        limit_types=('PC-TWA',),
    ),
    '珍珠岩粉尘': OELRule(
        project='珍珠岩粉尘',
        limit_types=('PC-TWA',),
    ),
    '蛭石粉尘': OELRule(
        project='蛭石粉尘',
        limit_types=('PC-TWA',),
    ),
    '重晶石粉尘': OELRule(
        project='重晶石粉尘',
        limit_types=('PC-TWA',),
    ),
    '其他粉尘a': OELRule(
        project='其他粉尘a',
        limit_types=('PC-TWA',),
    ),
    '白僵蚕孢子': OELRule(
        project='白僵蚕孢子',
        limit_types=('MAC',),
    ),
    '枯草杆菌蛋白酶': OELRule(
        project='枯草杆菌蛋白酶',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '工业酶': OELRule(
        project='工业酶',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    'N,N-二甲基乙酰胺': OELRule(
        project='N,N-二甲基乙酰胺',
        limit_types=('PC-TWA',),
    ),
    'N,N-二甲基甲酰胺': OELRule(
        project='N,N-二甲基甲酰胺',
        limit_types=('PC-TWA',),
    ),
    '苯酚': OELRule(
        project='苯酚',
        limit_types=('PC-TWA',),
    ),
    '乙酸酐': OELRule(
        project='乙酸酐',
        limit_types=('PC-TWA',),
    ),
    '丙烯酸丁酯': OELRule(
        project='丙烯酸丁酯',
        limit_types=('PC-TWA',),
    ),
    '氢氰酸': OELRule(
        project='氢氰酸',
        limit_types=('MAC',),
    ),
    '盐酸': OELRule(
        project='盐酸',
        limit_types=('MAC',),
    ),
    '氯化氢': OELRule(
        project='氯化氢',
        limit_types=('MAC',),
    ),
    '硫酸': OELRule(
        project='硫酸',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '三氧化硫': OELRule(
        project='三氧化硫',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '其他粉尘': OELRule(
        project='其他粉尘',
        limit_types=('PC-TWA',),
    ),
    '金属粉尘': OELRule(
        project='金属粉尘',
        limit_types=('PC-TWA',),
    ),
    '矽尘': OELRule(
        project='矽尘',
        limit_types=('PC-TWA',),
    ),
    '3-丁二烯': OELRule(
        project='3-丁二烯',
        limit_types=('PC-TWA',),
    ),
    '己烷': OELRule(
        project='己烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '庚烷': OELRule(
        project='庚烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '正戊烷': OELRule(
        project='正戊烷',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
    '丁醇': OELRule(
        project='丁醇',
        limit_types=('PC-TWA',),
    ),
    '丁醛': OELRule(
        project='丁醛',
        limit_types=('PC-TWA', 'PC-STEL'),
    ),
}
