# -*- coding: utf-8 -*-
# Copyright: Ankitects Pty Ltd and contributors
# Used/unused kanji list code originally by 'LaC'
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import unicodedata
from anki.utils import ids2str, splitFields
from aqt.webview import AnkiWebView
from aqt.qt import *
from aqt.utils import restoreGeom, saveGeom
from .notetypes import isJapaneseNoteType
from aqt import mw
config = mw.addonManager.getConfig(__name__)

# Backwards compatibility
try:
    UNICODE_EXISTS = bool(type(unicode)) # Python 2.X
except NameError:
    unicode = lambda *s: str(s) # Python 3+
try:
    range = xrange # Python 2.X
except NameError:
    pass # Python 3+

def isKanji(unichar):
    try:
        return unicodedata.name(unichar).find('CJK UNIFIED IDEOGRAPH') >= 0
    except ValueError:
        # a control character
        return False

class KanjiStats(object):

    def __init__(self, col, wholeCollection):
        self.col = col
        if wholeCollection:
            self.lim = ""
        else:
            self.lim = " and c.did in %s" % ids2str(self.col.decks.active())
        self._gradeHash = dict()
        for (name, chars), grade in zip(self.kanjiGrades,
                                        range(len(self.kanjiGrades))):
            for c in chars:
                self._gradeHash[c] = grade

    def kanjiGrade(self, unichar):
        return self._gradeHash.get(unichar, 0)

    # FIXME: as it's html, the width doesn't matter
    def kanjiCountStr(self, gradename, count, total=0, width=0):
        d = {'count': self.rjustfig(count, width), 'gradename': gradename}
        if total:
            d['total'] = self.rjustfig(total, width)
            d['percent'] = float(count)/total*100
            return ("%(gradename)s: %(count)s of %(total)s (%(percent)0.1f%%).") % d
        else:
            return ("%(count)s %(gradename)s kanji.") % d

    # FIXME: as it's html, the width doesn't matter
    def kanjiLearnTimePrevisionStr(self, gradename, count, total=0, width=0):
        d = {'count': self.rjustfig(count, width), 'gradename': gradename}
        if total:
            if gradename == "JLPT 5":
                d['days'] = round((total-count)/3)
            if gradename == "JLPT 4":
                d['days'] = round((total-count)/3)
            if gradename == "JLPT 3":
                d['days'] = round((total-count)/2)
            if gradename == "JLPT 2":
                d['days'] = round((total-count)/1)
            if gradename == "JLPT 1":
                d['days'] = round((total-count)/1)
            if d['days'] == 0:
                return ("%(gradename)s: Learning completed.") % d
            else:
                return ("%(gradename)s: %(days)s days left to learn all.") % d
        else:
            return ("")

    def rjustfig(self, n, width):
        n = unicode(n)
        return n + "&nbsp;" * (width - len(n))

    def genKanjiSets(self):
        self.kanjiSets = [set([]) for g in self.kanjiGrades]
        chars = set()
        for m in self.col.models.all():
            _noteName = m['name'].lower()
            if not isJapaneseNoteType(_noteName):
                continue

            idxs = []
            for c, name in enumerate(self.col.models.fieldNames(m)):
                for f in config['srcFields']:
                    if name == f:
                        idxs.append(c)
            for row in self.col.db.execute("""
select flds from notes where id in (
select n.id from cards c, notes n
where c.nid = n.id and mid = ? and c.queue > 0
%s) """ % self.lim, m['id']):
                flds = splitFields(row[0])
                for idx in idxs:
                    chars.update(flds[idx])
        for c in chars:
            if isKanji(c):
                self.kanjiSets[self.kanjiGrade(c)].add(c)

    def report(self):
        self.genKanjiSets()
        counts = [(name, len(found), len(all)) \
                  for (name, all), found in zip(self.kanjiGrades, self.kanjiSets)]
        out = ((("<h1>Kanji statistics</h1>The seen cards in this %s "
                 "contain:") % (self.lim and "deck" or "collection")) +
               "<ul>" +
               # total kanji unique
               ("<li>%d total unique kanji.</li>") %
               sum([c[1] for c in counts]))
        count = sum([c[1] for c in counts])
        d = {'count': self.rjustfig(count, 3)}
        total = sum([c[2] for c in counts])
        d['total'] = self.rjustfig(total,3)
        d['percent'] = float(count/total*100)
        out += ("<li>Total : %(count)s of %(total)s (%(percent)0.1f%%).</li>") % d
		#jlpt level
        out += "</ul><p/>" + (u"JLPT levels:") + "<p/><ul>"
        L = ["<li>" + self.kanjiCountStr(c[0],c[1],c[2], width=3) + "</li>"
			for c in counts[1:8]]
        out += "".join(L)
        out += "</ul>"
		#time to learn
        out += "</ul><p/>" + (u"Time to learn:") + "<p/><ul>"
        L = ["<li>" + self.kanjiLearnTimePrevisionStr(c[0],c[1],c[2], width=3) + "</li>"
			for c in counts[1:8]]
        out += "".join(L)
        out += "</ul>"
        return out

    def missingReport(self, check=None):
        if not check:
            check = lambda x, y: x not in y
            out = ("<h1>Missing</h1>")
        else:
            out = ("<h1>Seen</h1>")
        for grade in range(1, len(self.kanjiGrades)):
            missing = "".join(self.missingInGrade(grade, check))
            if not missing:
                continue
            out += "<h2>" + self.kanjiGrades[grade][0] + "</h2>"
            out += "<font size=+2>"
            out += self.mkEdict(missing)
            out += "</font>"
        return out + "<br/>"

    def mkEdict(self, kanji):
        out = "<font size=+2>"
        while 1:
            if not kanji:
                out += "</font>"
                return out
            # edict will take up to about 10 kanji at once
            out += self.edictKanjiLink(kanji[0:10])
            kanji = kanji[10:]

    def seenReport(self):
        return self.missingReport(lambda x, y: x in y)

    def nonJouyouReport(self):
        out = ("<h1>Non-Jouyou</h1>")
        out += self.mkEdict("".join(self.kanjiSets[0]))
        return out + "<br/>"

    def edictKanjiLink(self, kanji):
        base="http://nihongo.monash.edu/cgi-bin/wwwjdic?1MMJ"
        url=base + kanji
        return '<a href="%s">%s</a>' % (url, kanji)

    def missingInGrade(self, gradeNum, check):
        existingKanji = self.kanjiSets[gradeNum]
        totalKanji = self.kanjiGrades[gradeNum][1]
        return [k for k in totalKanji if check(k, existingKanji)]

    kanjiGrades = [
        (u'non-jouyou', ''),
        (u'JLPT 5', u'一七三上下中九二五人休先入八六円出十千口右名四土大天女子学小山川左年手日月木本校気水火生男白百目空立耳花見足車金雨万今会何分前北午半南友古国外多少店後新時書来東母毎父社聞行西言話語読買週道長間電食高魚安飲駅'),
        (u'JLPT 4', u'力夕字文早村林森正犬田町赤青音京体作元兄光冬切台合同回図地場声売夏夜太妹姉室家工市帰広引弟弱強心思教方明春昼曜朝楽歌止歩池海牛理用画知秋答紙考肉自色茶親計走近通遠野門頭顔風首鳥黒世主乗事仕代住使写勉動区医去味品員問始寒屋度待急悪意所持旅族暑暗有服業注洋漢物界病発県真着短研究終習者薬起転軽送進運都重銀開院集題館不以低便借働別堂好建料民特産英菜試説飯験貸質映洗私'),
        (u'JLPT 3', u'王石草交内原園当形才数晴活点番直科米組絵船記雪馬鳴両予他係全具列助勝化反取受号向君命和商夫守定実客宿対局平幸庭式役息悲想感打投指放昔曲期様横次歯決泳流消深港球由申登相礼神福等箱美育苦落葉表調談負路返追速遊部配酒陽面争付伝位例信候側共冷初利加努労単参告喜変失完官害察差席徒得必念愛成戦折敗散昨景最望未末束果機欠残殺求治法満然熱種積笑約給続置老良要覚観議費辞連達選関静願類飛件任似余備判制務因在報増夢妻婦容寄富居師常性情慣招支政断易格構演犯状現留破確示祖程精経絶罪職能術規解許識財貧責資賛迷退過適限険際雑非亡供値優処刻割勤危収否吸呼困存宅座忘探晩暮権欲段済疑痛窓背腹若訪認論警閉降除難頂彼偉違越煙押皆掛幾恐偶靴迎互御更込婚歳緒寝吹恥遅渡途怒倒盗到逃突猫杯髪抜疲怖浮舞払捕抱忙眠娘戻与頼'),
        (u'JLPT 2', u'玉竹糸虫貝丸公寺岩戸星毛算細線羽角谷雲麦黄倍坂委岸島州庫拾整板柱根植橋死氷油波温湖湯炭畑皮皿祭秒章童第筆級緑練荷血身農鉄階鼻令仲停健億兆児兵刷副勇包卒協印史司各周器囲固型塩央季孫希帯底府康改救札材栄案械極標歴毒泣浅浴清漁灯無焼照的省祝競管節粉結胃臣航芸衣訓課象貨貯賞軍輪辺量録陸順久仏仮価保修個像再刊券則効勢厚可営団圧均基境導布張復志応快承技授採接損故旧暴条枝査検武比永河液混減測準燃版独率略禁移税築綿総編績群耕製複設評講豊貿輸述逆造鉱銅防預領額並乱乳党冊劇卵善城域宇宙宝専将尊届展層巻干幼庁延律批担拝拡捨操敬暖机枚棒泉灰片異看砂簡紅純署翌胸脳臓著蒸蔵装裏補詞誌諸賃郵針革骨依鋭汚奥欧菓介較乾患換汗環甘缶含祈喫詰巨叫挟況狭隅掘傾恵肩賢軒枯雇硬肯荒郊香腰咲伺刺脂湿舟柔召床昇紹触伸辛震姓隻籍跡占双捜掃燥憎贈替袋濯畜駐超沈珍泥滴殿塗凍塔筒曇鈍軟悩濃泊薄爆肌般販被匹瓶普符膚封幅沸壁募坊帽磨埋溶踊絡粒了療涙零齢恋錬湾腕'),
        (u'JLPT 1', u'刀弓汽矢里丁宮帳昭笛羊詩豆倉典功博唱士巣径挙旗松梅氏牧票紀脈腸芽街郡鏡隊養俵句墓属幹序弁往徳恩態提敵桜潔災益眼素統織義肥興舌舎衛証謝護賀酸銭飼仁俳傷創厳后垂奏奮姿孝宗宣密寸射就尺己幕従忠憲我推揮朗染株模樹沿派源潮激熟班皇盛盟磁秘穀穴筋策糖系納絹縦縮聖肺臨至蚕衆裁視覧討訳誕誠誤貴遺郷鋼閣陛障亜哀握扱威尉慰為維緯井壱逸稲芋姻陰隠韻渦浦影詠疫悦謁閲宴援炎猿縁鉛凹殴翁沖憶乙卸穏佳嫁寡暇架禍稼箇華蚊雅餓塊壊怪悔懐戒拐劾慨概涯該垣嚇核殻獲穫郭隔岳潟喝括渇滑褐轄且刈冠勘勧喚堪寛憾敢棺款歓監緩肝艦貫還鑑閑陥頑企奇岐忌既棋棄軌輝飢騎鬼偽儀宜戯擬欺犠菊吉却脚虐丘及朽窮糾拒拠虚距享凶峡恭狂矯脅響驚仰凝暁斤琴緊菌襟謹吟駆愚虞遇屈繰桑勲薫刑啓契慶憩掲携渓継茎蛍鶏鯨撃傑倹兼剣圏堅嫌懸献謙遣顕幻弦玄孤弧誇顧鼓呉娯悟碁侯坑孔巧恒慌抗拘控攻江洪溝甲稿絞綱衡貢購酵項剛拷豪克酷獄墾恨懇昆紺魂佐唆詐鎖債催宰彩栽砕斎載剤崎削搾索錯撮擦傘惨桟暫嗣施旨祉紫肢諮賜雌侍慈滋璽軸執漆疾芝赦斜煮遮蛇邪勺爵酌釈寂朱殊狩珠趣儒寿需囚愁秀臭襲酬醜充汁渋獣銃叔淑粛塾俊瞬准循旬殉潤盾巡遵庶叙徐償匠升奨宵尚彰抄掌晶沼渉焦症硝礁祥称粧肖衝訟詔詳鐘丈冗剰壌嬢浄畳譲醸錠嘱飾殖辱侵唇娠審慎振浸紳薪診刃尋甚尽迅陣酢帥炊睡粋衰遂酔錘随髄崇枢据杉澄瀬畝是征牲誓請逝斉惜斥析拙摂窃仙扇栓潜旋繊薦践遷銑鮮漸禅繕塑措疎礎租粗訴阻僧喪壮挿曹槽荘葬藻遭霜騒促即俗賊堕妥惰駄耐怠泰滞胎逮滝卓択拓沢託濁諾但奪脱棚丹嘆淡端胆鍛壇弾痴稚致蓄逐秩窒嫡抽衷鋳弔彫徴懲挑眺聴脹跳勅朕鎮陳津墜塚漬坪釣亭偵貞呈堤帝廷抵締艇訂逓邸摘哲徹撤迭添吐斗奴唐悼搭桃棟痘謄踏透陶騰闘洞胴峠匿督篤凸屯豚縄尼弐如尿妊忍寧粘把覇婆廃排輩培媒賠陪伯拍舶迫漠縛鉢伐罰閥伴帆搬畔繁藩範煩頒盤蛮卑妃扉披泌碑罷避尾微姫漂描苗浜賓頻敏扶敷腐譜賦赴附侮伏覆噴墳憤紛雰丙併塀幣弊柄癖偏遍舗穂慕簿倣俸奉峰崩泡砲縫胞芳褒邦飽乏傍剖妨房某冒紡肪膨謀墨撲朴没堀奔翻凡盆摩魔麻膜又抹繭慢漫魅岬妙矛霧婿銘滅免茂妄猛盲網耗黙紋匁厄躍柳愉癒諭唯幽悠憂猶裕誘雄融誉庸揚揺擁窯謡抑翼羅裸雷酪欄濫吏履痢離硫隆竜慮虜僚寮涼猟糧陵倫厘隣塁累励鈴隷霊麗暦劣烈裂廉炉露廊楼浪漏郎賄惑枠渚媛唄嵐亀伎沙駒喉虎拳鹿采須憧汰爽鶴椎旦梨奈那瞳藤賭眉虹弥冶呂瑠瞭璃藍湧睦僕')
        ]

def genKanjiStats():
    wholeCollection = mw.state == "deckBrowser"
    s = KanjiStats(mw.col, wholeCollection)
    rep = s.report()
    rep += s.seenReport()
    rep += s.missingReport()
    rep += s.nonJouyouReport()
    return rep

def onKanjiStats():
    mw.progress.start(immediate=True)
    rep = genKanjiStats()
    d = QDialog(mw)
    l = QVBoxLayout()
    l.setContentsMargins(0,0,0,0)
    w = AnkiWebView()
    l.addWidget(w)
    w.stdHtml(rep)
    bb = QDialogButtonBox(QDialogButtonBox.Close)
    l.addWidget(bb)
    bb.rejected.connect(d.reject)
    d.setLayout(l)
    d.resize(500, 400)
    restoreGeom(d, "kanjistats")
    mw.progress.finish()
    d.exec_()
    saveGeom(d, "kanjistats")

def createMenu():
    a = QAction(mw)
    a.setText("Kanji JLPT Stats")
    mw.form.menuTools.addAction(a)
    a.triggered.connect(onKanjiStats)

createMenu()
