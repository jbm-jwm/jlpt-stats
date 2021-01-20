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
from . import util

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
                d['days'] = round((total-count)/(util.setting('KanjiLearnedByDayjplpt5') if util.setting('KanjiLearnedByDayjplpt5') > 0 else 1))
            if gradename == "JLPT 4":
                d['days'] = round((total-count)/(util.setting('KanjiLearnedByDayjplpt4') if util.setting('KanjiLearnedByDayjplpt4') > 0 else 1))
            if gradename == "JLPT 3":
                d['days'] = round((total-count)/(util.setting('KanjiLearnedByDayjplpt3') if util.setting('KanjiLearnedByDayjplpt3') > 0 else 1))
            if gradename == "JLPT 2":
                d['days'] = round((total-count)/(util.setting('KanjiLearnedByDayjplpt2') if util.setting('KanjiLearnedByDayjplpt2') > 0 else 1))
            if gradename == "JLPT 1":
                d['days'] = round((total-count)/(util.setting('KanjiLearnedByDayjplpt1') if util.setting('KanjiLearnedByDayjplpt1') > 0 else 1))
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
        (u'JLPT 5', u'一右雨円下何火外学間気休金九月見五午後語校行高国今左三山四子時七車十出書女小上食人水生西先千川前大男中長天電土東読南二日入年白八半百父聞母北本毎万名木友来六話'),
        (u'JLPT 4', u'悪安以意医員飲院運映英駅屋音夏家歌花画会海界開楽漢館帰起急究牛去魚京強教業近銀空兄計建犬研験元言古公口工広考黒作仕使始姉思止死私紙試事字持自室質写社者借主手秋終習週集住重春少場色心新真親図世正青赤切早走送足族多体待貸代台題知地茶着昼注朝町鳥通弟店転田度冬答動同堂道特肉買売発飯病品不風服物文別勉歩方妹味明目問夜野有夕曜洋用理立旅料力'),
        (u'JLPT 3', u'愛暗位偉易違育因引泳越園演煙遠押横王化加科果過解回皆絵害格確覚掛割活寒完官感慣観関顔願危喜寄幾期機規記疑議客吸求球給居許供共恐局曲勤苦具偶靴君係形景経警迎欠決件権険原現限呼互御誤交候光向好幸更構港降号合刻告込困婚差座最妻才歳済際在罪財昨察殺雑参散産賛残市師指支資歯似次治示耳辞式識失実若取守種酒首受収宿術処初所緒助除勝商招消笑乗常情状職信寝深申神進吹数制性成政晴精声静席昔石積責折説雪絶戦洗船選然全祖組想争相窓草増側息束速続存他太打対退宅達単探断段談値恥置遅調頂直追痛定庭程適点伝徒渡登途都努怒倒投盗当等到逃頭働得突内難任認猫熱念能破馬敗杯背配箱髪抜判反犯晩番否彼悲疲費非飛備美必表貧付夫婦富怖浮負舞部福腹払平閉米変返便捕暮報抱放法訪亡忘忙望末満未民眠務夢娘命迷鳴面戻役約薬優由遊予余与容様葉要陽欲頼落利流留両良類例冷礼列連路労老論和'),
        (u'JLPT 2', u'圧依囲委移胃衣域印宇羽雲営栄永液延塩汚央奥黄億温河荷菓課貨介快改械灰階貝各角革額乾刊巻干患換汗甘管簡缶丸岸岩希机祈季技喫詰逆久旧巨漁競協境橋況胸極玉均禁区隅訓群軍型敬軽芸劇血県肩軒減個固庫戸枯湖効厚硬紅航講郊鉱香腰骨根混査砂再採祭細菜材坂咲冊刷札皿算刺史枝糸脂詞誌児寺捨弱周州拾舟柔祝述準純順署諸召将床昇焼照省章紹象賞城畳植触伸森臣辛針震勢姓星清税績接設占専泉浅線双層捜掃総装像憎臓蔵贈則卒孫尊損村帯替袋濯谷炭短団池築竹仲柱虫駐貯兆庁超珍低停底泥鉄塗党凍塔島湯灯筒導童毒届曇乳脳農波拝倍泊薄爆麦肌板版販比皮被鼻匹筆氷秒瓶布府普符武封副幅複沸仏粉兵並片辺補包宝豊帽暴棒貿防磨埋枚綿毛門油輸勇郵預溶踊浴絡卵裏陸律略了涼療量領緑林輪涙令零齢歴恋練録湾腕鋭欧含叫挟掘傾券賢雇耕肯荒伺湿承蒸隻籍跡燥造測担畜著沈滴殿銅鈍軟燃悩濃般膚復編募幼翌乱粒'),
        (u'JLPT 1', u'握扱案杏異井壱芋隠影衛益宴援炎猿縁鉛往応沖憶仮価嫁暇華蚊我芽賀壊怪悔懐戒涯街核穫較閣岳潟括且叶堪幹憾環監看肝眼頑企器基奇岐旗既棄汽紀貴鬼亀宜義菊吉脚丘及宮弓救泣級挙距狭興郷鏡響仰暁琴筋緊菌句熊栗繰郡刑契径恵憩携桂鶏鯨撃激傑穴結健剣憲懸検絹遣厳源玄己弧故虎鼓呉悟護功后巧康抗攻江皇絞鋼項豪穀酷魂佐鎖栽災斎崎索桜撮傘蚕酸暫司士姿志施氏紫肢至視詩飼侍滋鹿芝射煮謝蛇邪寂趣授囚宗就修臭襲汁渋縦銃瞬循盾巡暑徐唱奨掌昭松焦症硝証詳障冗嬢条譲飾侵唇娠振薪診刃尋尽迅酢睡随杉是整牲盛製節舌仙宣扇染潜鮮善素倉奏操巣霜騒即属駄耐態滞逮隊第沢只但奪脱棚端誕弾暖致宙丁帳張彫懲挑暢眺聴腸蝶賃津漬釣堤抵締訂敵笛哲徹典展吐奴刀桃糖統豆踏瞳徳督独豚奈凪縄弐虹妊寧粘納派俳輩培梅伯博拍漠罰伴帆煩扉批披秘避尾微眉姫媛標票評描浜敷奮紛雰塀壁癖弁保墓崩泡砲褒邦房冒僕墨牧凡魔麻幕又抹慢魅密脈妙霧免模妄盲黙紋也矢訳柚裕誘融揚揺羊養抑翼裸雷嵐覧吏履梨離率慮僚寮隣励鈴麗暦劣露廊漏郎惑綺亜阿哀葵茜渥旭梓絢綾鮎伊威尉惟慰為維緯遺亥郁磯逸稲允姻胤陰韻卯丑渦唄浦叡瑛詠疫悦謁閲沿艶苑於凹旺殴翁乙卸恩穏伽佳嘉寡架禍稼箇茄霞雅餓塊拐魁凱劾慨概該馨垣嚇拡殻獲郭隔喝渇滑褐轄樺株鎌茅刈侃冠勘勧喚寛敢棺款歓緩艦莞貫還鑑閑陥巌伎嬉忌揮棋毅稀軌輝飢騎偽儀戯擬欺犠誼鞠橘却虐朽窮糾拒拠虚亨享凶匡喬峡恭狂矯脅驚凝尭桐錦斤欣欽芹衿襟謹吟玖駆駒愚虞遇屈桑勲薫袈啓圭慶慧掲渓系継茎蛍潔倹兼圏堅嫌拳献謙顕幻弦絃孤胡誇顧伍娯梧瑚碁鯉侯倖坑孔宏弘恒拘控昂晃洪浩溝甲稿紘綱衡貢購酵鴻剛拷克獄墾恨懇昆紺唆嵯沙瑳詐裟債催哉宰彩采砕裁載剤冴削搾朔策錯笹擦皐惨桟燦嗣旨祉諮賜雌慈爾磁蒔汐軸執漆疾偲舎赦斜紗遮勺尺爵酌釈朱殊狩珠儒樹需愁洲秀衆酬醜充従獣叔淑縮粛塾熟俊峻竣舜駿准旬殉淳潤遵曙渚庶叙序恕傷償匠升宵尚庄彰抄捷昌晶梢沼渉礁祥称肖菖蕉衝訟詔鐘丞剰壌浄穣醸錠嘱殖織辱審慎晋榛浸秦紳仁甚陣須垂帥推炊粋翠衰遂酔錘瑞髄崇嵩枢雛据澄寸瀬畝征聖誠誓請逝斉惜斥析碩拙摂窃栓旋繊薦践遷銭銑漸禅繕塑措疎礎租粗訴阻僧創喪壮爽惣挿曹槽綜聡荘葬蒼藻遭促俗賊汰堕妥惰怠泰胎黛鯛鷹滝卓啄択拓琢託濁諾辰巽丹嘆旦淡胆鍛壇檀智痴稚蓄逐秩窒嫡忠抽衷鋳猪弔徴潮脹跳勅朕鎮陳墜椎塚槻蔦椿坪紬鶴亭偵貞呈帝廷悌提禎艇逓邸摘撤迭添斗杜悼搭棟痘藤討謄透陶騰闘憧洞胴峠匿篤凸寅酉屯惇敦那捺楠尼如尿忍乃之巴把覇婆廃排肺媒賠陪萩舶迫縛肇鉢伐閥鳩隼搬班畔繁藩範頒盤蛮卑妃斐泌碑緋罷肥柊彦俵彪漂苗彬賓頻敏扶腐芙譜賦赴附侮楓蕗伏覆噴墳憤丙併幣弊柄陛碧偏遍舗甫輔穂慕簿倣俸奉峰朋縫胞芳萌飽鳳鵬乏傍剖妨某紡肪膨謀撲朴睦没堀奔翻盆摩槙膜柾亦繭麿漫巳岬稔矛椋婿盟銘滅茂孟猛網耗匁冶耶弥厄躍靖柳愉癒諭唯佑宥幽悠憂湧猶祐邑雄誉庸擁楊窯耀蓉謡遥羅酪欄濫藍蘭李璃痢琉硫隆竜虜亮凌猟瞭稜糧諒遼陵倫厘琳臨麟瑠塁累伶嶺怜玲隷霊烈裂廉蓮錬呂炉朗楼浪禄倭賄枠亘侑勁奎崚彗昴晏晨晟暉栞椰毬洸洵滉漱澪燎燿瑶皓眸笙綸翔脩茉莉菫詢諄赳迪頌颯黎凜熙')
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
