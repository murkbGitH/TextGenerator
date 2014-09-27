# -*- coding: utf-8 -*-

u"""
与えられた文書からマルコフ連鎖のためのチェーン（連鎖）を作成して、DBに保存するファイル
"""

import unittest

import re
import MeCab
import sqlite3
from collections import defaultdict


class PrepareChain(object):
    u"""
    チェーンを作成してDBに保存するクラス
    """

    BEGIN = u"__BEGIN_SENTENCE__"
    END = u"__END_SENTENCE__"

    DB_PATH = "chain.db"
    DB_SCHEMA_PATH = "schema.sql"

    def __init__(self, text):
        u"""
        初期化メソッド
        @param text チェーンを生成するための文章
        """
        if isinstance(text, str):
            text = text.decode("utf-8")
        self.text = text

        # 形態素解析用タガー
        self.tagger = MeCab.Tagger('-Ochasen')

    def make_triplet_freqs(self):
        u"""
        形態素解析から3つ組の出現回数まで
        @return 3つ組とその出現回数の辞書 key: 3つ組（タプル） val: 出現回数
        """
        # 長い文章をセンテンス毎に分割
        sentences = self._divide(self.text)

        # 3つ組の出現回数
        triplet_freqs = defaultdict(int)

        # センテンス毎に3つ組にする
        for sentence in sentences:
            # 形態素解析
            morphemes = self._morphological_analysis(sentence)
            # 3つ組をつくる
            triplets = self._make_triplet(morphemes)
            # 出現回数を加算
            for (triplet, n) in triplets.items():
                triplet_freqs[triplet] += n

        return triplet_freqs

    def _divide(self, text):
        u"""
        「。」や改行などで区切られた長い文章を一文ずつに分ける
        @param text 分割前の文章
        @return 一文ずつの配列
        """
        # 改行文字以外の分割文字（正規表現表記）
        delimiter = u"。|．|\."

        # 全ての分割文字を改行文字に置換（splitしたときに「。」などの情報を無くさないため）
        text = re.sub(ur"({0})".format(delimiter), r"\1\n", text)

        # 改行文字で分割
        sentences = text.splitlines()

        # 前後の空白文字を削除
        sentences = [sentence.strip() for sentence in sentences]

        return sentences

    def _morphological_analysis(self, sentence):
        u"""
        一文を形態素解析する
        @param sentence 一文
        @return 形態素で分割された配列
        """
        morphemes = []
        sentence = sentence.encode("utf-8")
        node = self.tagger.parseToNode(sentence)
        while node:
            if node.posid != 0:
                morpheme = node.surface.decode("utf-8")
                morphemes.append(morpheme)
            node = node.next
        return morphemes

    def _make_triplet(self, morphemes):
        u"""
        形態素解析で分割された配列を、形態素毎に3つ組にしてその出現回数を数える
        @param morphemes 形態素配列
        @return 3つ組とその出現回数の辞書 key: 3つ組（タプル） val: 出現回数
        """
        # 3つ組をつくれない場合は終える
        if len(morphemes) < 3:
            return {}

        # 出現回数の辞書
        triplet_freqs = defaultdict(int)

        # 繰り返し
        for i in xrange(len(morphemes)-2):
            triplet = tuple(morphemes[i:i+3])
            triplet_freqs[triplet] += 1

        # beginを追加
        triplet = (PrepareChain.BEGIN, morphemes[0], morphemes[1])
        triplet_freqs[triplet] = 1

        # endを追加
        triplet = (morphemes[-2], morphemes[-1], PrepareChain.END)
        triplet_freqs[triplet] = 1

        return triplet_freqs

    def save(self, triplet_freqs, init=False):
        u"""
        3つ組毎に出現回数をDBに保存
        @param triplet_freqs 3つ組とその出現回数の辞書 key: 3つ組（タプル） val: 出現回数
        """
        # DBオープン
        con = sqlite3.connect(PrepareChain.DB_PATH)

        # 初期化から始める場合
        if init:
            # DBの初期化
            with open(PrepareChain.DB_SCHEMA_PATH, "r") as f:
                schema = f.read()
                con.executescript(schema)

            # データ整形
            datas = [(triplet[0], triplet[1], triplet[2], freq) for (triplet, freq) in triplet_freqs.items()]

            # データ挿入
            p_statement = u"insert into chain_freqs (prefix1, prefix2, suffix, freq) values (?, ?, ?, ?)"
            con.executemany(p_statement, datas)

        # コミットしてクローズ
        con.commit()
        con.close()

    def show(self, triplet_freqs):
        u"""
        3つ組毎の出現回数を出力する
        @param triplet_freqs 3つ組とその出現回数の辞書 key: 3つ組（タプル） val: 出現回数
        """
        for triplet in triplet_freqs:
            print "|".join(triplet), "\t", triplet_freqs[triplet]


class TestFunctions(unittest.TestCase):
    u"""
    テスト用クラス
    """

    def setUp(self):
        u"""
        テストが実行される前に実行される
        """
        self.text = u"こんにちは。　今日は、楽しい運動会です。hello world.我輩は猫である\n  名前はまだない。我輩は犬である\r\n名前は決まってるよ"
        self.chain = PrepareChain(self.text)

    def test_make_triplet_freqs(self):
        u"""
        全体のテスト
        """
        triplet_freqs = self.chain.make_triplet_freqs()
        answer = {(u"__BEGIN_SENTENCE__", u"今日", u"は"): 1, (u"今日", u"は", u"、"): 1, (u"は", u"、", u"楽しい"): 1, (u"、", u"楽しい", u"運動会"): 1, (u"楽しい", u"運動会", u"です"): 1, (u"運動会", u"です", u"。"): 1, (u"です", u"。", u"__END_SENTENCE__"): 1, (u"__BEGIN_SENTENCE__", u"hello", u"world"): 1, (u"hello", u"world", u"."): 1, (u"world", u".", u"__END_SENTENCE__"): 1, (u"__BEGIN_SENTENCE__", u"我輩", u"は"): 2, (u"我輩", u"は", u"猫"): 1, (u"は", u"猫", u"で"): 1, (u"猫", u"で", u"ある"): 1, (u"で", u"ある", u"__END_SENTENCE__"): 2, (u"__BEGIN_SENTENCE__", u"名前", u"は"): 2, (u"名前", u"は", u"まだ"): 1, (u"は", u"まだ", u"ない"): 1, (u"まだ", u"ない", u"。"): 1, (u"ない", u"。", u"__END_SENTENCE__"): 1, (u"我輩", u"は", u"犬"): 1, (u"は", u"犬", u"で"): 1, (u"犬", u"で", u"ある"): 1, (u"名前", u"は", u"決まっ"): 1, (u"は", u"決まっ", u"てる"): 1, (u"決まっ", u"てる", u"よ"): 1, (u"てる", u"よ", u"__END_SENTENCE__"): 1}
        self.assertEqual(triplet_freqs, answer)

    def test_divide(self):
        u"""
        一文ずつに分割するテスト
        """
        sentences = self.chain._divide(self.text)
        answer = [u"こんにちは。", u"今日は、楽しい運動会です。", u"hello world.", u"我輩は猫である", u"名前はまだない。", u"我輩は犬である", u"名前は決まってるよ"]
        self.assertEqual(sentences.sort(), answer.sort())

    def test_morphological_analysis(self):
        u"""
        形態素解析用のテスト
        """
        sentence = u"今日は、楽しい運動会です。"
        morphemes = self.chain._morphological_analysis(sentence)
        answer = [u"今日", u"は", u"、", u"楽しい", u"運動会", u"です", u"。"]
        self.assertEqual(morphemes.sort(), answer.sort())

    def test_make_triplet(self):
        u"""
        形態素毎に3つ組にしてその出現回数を数えるテスト
        """
        morphemes = [u"今日", u"は", u"、", u"楽しい", u"運動会", u"です", u"。"]
        triplet_freqs = self.chain._make_triplet(morphemes)
        answer = {(u"__BEGIN_SENTENCE__", u"今日", u"は"): 1, (u"今日", u"は", u"、"): 1, (u"は", u"、", u"楽しい"): 1, (u"、", u"楽しい", u"運動会"): 1, (u"楽しい", u"運動会", u"です"): 1, (u"運動会", u"です", u"。"): 1, (u"です", u"。", u"__END_SENTENCE__"): 1}
        self.assertEqual(triplet_freqs, answer)

    def test_make_triplet_too_short(self):
        u"""
        形態素毎に3つ組にしてその出現回数を数えるテスト
        ただし、形態素が少なすぎる場合
        """
        morphemes = [u"こんにちは", u"。"]
        triplet_freqs = self.chain._make_triplet(morphemes)
        answer = {}
        self.assertEqual(triplet_freqs, answer)

    def test_make_triplet_3morphemes(self):
        u"""
        形態素毎に3つ組にしてその出現回数を数えるテスト
        ただし、形態素がちょうど3つの場合
        """
        morphemes = [u"hello", u"world", u"."]
        triplet_freqs = self.chain._make_triplet(morphemes)
        answer = {(u"__BEGIN_SENTENCE__", u"hello", u"world"): 1, (u"hello", u"world", u"."): 1, (u"world", u".", u"__END_SENTENCE__"): 1}
        self.assertEqual(triplet_freqs, answer)

    def tearDown(self):
        u"""
        テストが実行された後に実行される
        """
        pass


if __name__ == '__main__':
    # unittest.main()

    # 『檸檬』梶井基次郎
    text = u"""えたいの知れない不吉な塊が私の心を始終圧おさえつけていた。焦躁しょうそうと言おうか、嫌悪と言おうか――酒を飲んだあとに宿酔ふつかよいがあるように、酒を毎日飲んでいると宿酔に相当した時期がやって来る。それが来たのだ。これはちょっといけなかった。結果した肺尖はいせんカタルや神経衰弱がいけないのではない。また背を焼くような借金などがいけないのではない。いけないのはその不吉な塊だ。以前私を喜ばせたどんな美しい音楽も、どんな美しい詩の一節も辛抱がならなくなった。蓄音器を聴かせてもらいにわざわざ出かけて行っても、最初の二三小節で不意に立ち上がってしまいたくなる。何かが私を居堪いたたまらずさせるのだ。それで始終私は街から街を浮浪し続けていた。
　何故なぜだかその頃私は見すぼらしくて美しいものに強くひきつけられたのを覚えている。風景にしても壊れかかった街だとか、その街にしてもよそよそしい表通りよりもどこか親しみのある、汚い洗濯物が干してあったりがらくたが転がしてあったりむさくるしい部屋が覗のぞいていたりする裏通りが好きであった。雨や風が蝕むしばんでやがて土に帰ってしまう、と言ったような趣きのある街で、土塀どべいが崩れていたり家並が傾きかかっていたり――勢いのいいのは植物だけで、時とするとびっくりさせるような向日葵ひまわりがあったりカンナが咲いていたりする。
　時どき私はそんな路を歩きながら、ふと、そこが京都ではなくて京都から何百里も離れた仙台とか長崎とか――そのような市へ今自分が来ているのだ――という錯覚を起こそうと努める。私は、できることなら京都から逃げ出して誰一人知らないような市へ行ってしまいたかった。第一に安静。がらんとした旅館の一室。清浄な蒲団ふとん。匂においのいい蚊帳かやと糊のりのよくきいた浴衣ゆかた。そこで一月ほど何も思わず横になりたい。希ねがわくはここがいつの間にかその市になっているのだったら。――錯覚がようやく成功しはじめると私はそれからそれへ想像の絵具を塗りつけてゆく。なんのことはない、私の錯覚と壊れかかった街との二重写しである。そして私はその中に現実の私自身を見失うのを楽しんだ。
　私はまたあの花火というやつが好きになった。花火そのものは第二段として、あの安っぽい絵具で赤や紫や黄や青や、さまざまの縞模様しまもようを持った花火の束、中山寺の星下り、花合戦、枯れすすき。それから鼠花火ねずみはなびというのは一つずつ輪になっていて箱に詰めてある。そんなものが変に私の心を唆そそった。
　それからまた、びいどろという色硝子ガラスで鯛や花を打ち出してあるおはじきが好きになったし、南京玉なんきんだまが好きになった。またそれを嘗なめてみるのが私にとってなんともいえない享楽だったのだ。あのびいどろの味ほど幽かすかな涼しい味があるものか。私は幼い時よくそれを口に入れては父母に叱られたものだが、その幼時のあまい記憶が大きくなって落ち魄ぶれた私に蘇よみがえってくる故せいだろうか、まったくあの味には幽かすかな爽さわやかななんとなく詩美と言ったような味覚が漂って来る。
　察しはつくだろうが私にはまるで金がなかった。とは言えそんなものを見て少しでも心の動きかけた時の私自身を慰めるためには贅沢ぜいたくということが必要であった。二銭や三銭のもの――と言って贅沢なもの。美しいもの――と言って無気力な私の触角にむしろ媚こびて来るもの。――そう言ったものが自然私を慰めるのだ。
　生活がまだ蝕むしばまれていなかった以前私の好きであった所は、たとえば丸善であった。赤や黄のオードコロンやオードキニン。洒落しゃれた切子細工や典雅なロココ趣味の浮模様を持った琥珀色や翡翠色ひすいいろの香水壜こうすいびん。煙管きせる、小刀、石鹸せっけん、煙草たばこ。私はそんなものを見るのに小一時間も費すことがあった。そして結局一等いい鉛筆を一本買うくらいの贅沢をするのだった。しかしここももうその頃の私にとっては重くるしい場所に過ぎなかった。書籍、学生、勘定台、これらはみな借金取りの亡霊のように私には見えるのだった。
　ある朝――その頃私は甲の友達から乙の友達へというふうに友達の下宿を転々として暮らしていたのだが――友達が学校へ出てしまったあとの空虚な空気のなかにぽつねんと一人取り残された。私はまたそこから彷徨さまよい出なければならなかった。何かが私を追いたてる。そして街から街へ、先に言ったような裏通りを歩いたり、駄菓子屋の前で立ち留どまったり、乾物屋の乾蝦ほしえびや棒鱈ぼうだらや湯葉ゆばを眺めたり、とうとう私は二条の方へ寺町を下さがり、そこの果物屋で足を留とめた。ここでちょっとその果物屋を紹介したいのだが、その果物屋は私の知っていた範囲で最も好きな店であった。そこは決して立派な店ではなかったのだが、果物屋固有の美しさが最も露骨に感ぜられた。果物はかなり勾配の急な台の上に並べてあって、その台というのも古びた黒い漆塗うるしぬりの板だったように思える。何か華やかな美しい音楽の快速調アッレグロの流れが、見る人を石に化したというゴルゴンの鬼面――的なものを差しつけられて、あんな色彩やあんなヴォリウムに凝こり固まったというふうに果物は並んでいる。青物もやはり奥へゆけばゆくほど堆うず高く積まれている。――実際あそこの人参葉にんじんばの美しさなどは素晴すばらしかった。それから水に漬つけてある豆だとか慈姑くわいだとか。
　またそこの家の美しいのは夜だった。寺町通はいったいに賑にぎやかな通りで――と言って感じは東京や大阪よりはずっと澄んでいるが――飾窓の光がおびただしく街路へ流れ出ている。それがどうしたわけかその店頭の周囲だけが妙に暗いのだ。もともと片方は暗い二条通に接している街角になっているので、暗いのは当然であったが、その隣家が寺町通にある家にもかかわらず暗かったのが瞭然はっきりしない。しかしその家が暗くなかったら、あんなにも私を誘惑するには至らなかったと思う。もう一つはその家の打ち出した廂ひさしなのだが、その廂が眼深まぶかに冠った帽子の廂のように――これは形容というよりも、「おや、あそこの店は帽子の廂をやけに下げているぞ」と思わせるほどなので、廂の上はこれも真暗なのだ。そう周囲が真暗なため、店頭に点つけられた幾つもの電燈が驟雨しゅううのように浴びせかける絢爛けんらんは、周囲の何者にも奪われることなく、ほしいままにも美しい眺めが照らし出されているのだ。裸の電燈が細長い螺旋棒らせんぼうをきりきり眼の中へ刺し込んでくる往来に立って、また近所にある鎰屋かぎやの二階の硝子ガラス窓をすかして眺めたこの果物店の眺めほど、その時どきの私を興がらせたものは寺町の中でも稀まれだった。
　その日私はいつになくその店で買物をした。というのはその店には珍しい檸檬れもんが出ていたのだ。檸檬などごくありふれている。がその店というのも見すぼらしくはないまでもただあたりまえの八百屋に過ぎなかったので、それまであまり見かけたことはなかった。いったい私はあの檸檬が好きだ。レモンエロウの絵具をチューブから搾り出して固めたようなあの単純な色も、それからあの丈たけの詰まった紡錘形の恰好かっこうも。――結局私はそれを一つだけ買うことにした。それからの私はどこへどう歩いたのだろう。私は長い間街を歩いていた。始終私の心を圧えつけていた不吉な塊がそれを握った瞬間からいくらか弛ゆるんで来たとみえて、私は街の上で非常に幸福であった。あんなに執拗しつこかった憂鬱が、そんなものの一顆いっかで紛らされる――あるいは不審なことが、逆説的なほんとうであった。それにしても心というやつはなんという不可思議なやつだろう。
　その檸檬の冷たさはたとえようもなくよかった。その頃私は肺尖はいせんを悪くしていていつも身体に熱が出た。事実友達の誰彼だれかれに私の熱を見せびらかすために手の握り合いなどをしてみるのだが、私の掌が誰のよりも熱かった。その熱い故せいだったのだろう、握っている掌から身内に浸み透ってゆくようなその冷たさは快いものだった。
　私は何度も何度もその果実を鼻に持っていっては嗅かいでみた。それの産地だというカリフォルニヤが想像に上って来る。漢文で習った「売柑者之言」の中に書いてあった「鼻を撲うつ」という言葉が断きれぎれに浮かんで来る。そしてふかぶかと胸一杯に匂やかな空気を吸い込めば、ついぞ胸一杯に呼吸したことのなかった私の身体や顔には温い血のほとぼりが昇って来てなんだか身内に元気が目覚めて来たのだった。……
　実際あんな単純な冷覚や触覚や嗅覚や視覚が、ずっと昔からこればかり探していたのだと言いたくなったほど私にしっくりしたなんて私は不思議に思える――それがあの頃のことなんだから。
　私はもう往来を軽やかな昂奮に弾んで、一種誇りかな気持さえ感じながら、美的装束をして街を※(「さんずい＋闊」、第4水準2-79-45)歩かっぽした詩人のことなど思い浮かべては歩いていた。汚れた手拭の上へ載せてみたりマントの上へあてがってみたりして色の反映を量はかったり、またこんなことを思ったり、
　――つまりはこの重さなんだな。――
　その重さこそ常つねづね尋ねあぐんでいたもので、疑いもなくこの重さはすべての善いものすべての美しいものを重量に換算して来た重さであるとか、思いあがった諧謔心かいぎゃくしんからそんな馬鹿げたことを考えてみたり――なにがさて私は幸福だったのだ。
　どこをどう歩いたのだろう、私が最後に立ったのは丸善の前だった。平常あんなに避けていた丸善がその時の私にはやすやすと入れるように思えた。
「今日は一ひとつ入ってみてやろう」そして私はずかずか入って行った。
　しかしどうしたことだろう、私の心を充たしていた幸福な感情はだんだん逃げていった。香水の壜にも煙管きせるにも私の心はのしかかってはゆかなかった。憂鬱が立て罩こめて来る、私は歩き廻った疲労が出て来たのだと思った。私は画本の棚の前へ行ってみた。画集の重たいのを取り出すのさえ常に増して力が要るな！　と思った。しかし私は一冊ずつ抜き出してはみる、そして開けてはみるのだが、克明にはぐってゆく気持はさらに湧いて来ない。しかも呪われたことにはまた次の一冊を引き出して来る。それも同じことだ。それでいて一度バラバラとやってみなくては気が済まないのだ。それ以上は堪たまらなくなってそこへ置いてしまう。以前の位置へ戻すことさえできない。私は幾度もそれを繰り返した。とうとうおしまいには日頃から大好きだったアングルの橙色だいだいろの重い本までなおいっそうの堪たえがたさのために置いてしまった。――なんという呪われたことだ。手の筋肉に疲労が残っている。私は憂鬱になってしまって、自分が抜いたまま積み重ねた本の群を眺めていた。
　以前にはあんなに私をひきつけた画本がどうしたことだろう。一枚一枚に眼を晒さらし終わって後、さてあまりに尋常な周囲を見廻すときのあの変にそぐわない気持を、私は以前には好んで味わっていたものであった。……
「あ、そうだそうだ」その時私は袂たもとの中の檸檬れもんを憶い出した。本の色彩をゴチャゴチャに積みあげて、一度この檸檬で試してみたら。「そうだ」
　私にまた先ほどの軽やかな昂奮が帰って来た。私は手当たり次第に積みあげ、また慌あわただしく潰し、また慌しく築きあげた。新しく引き抜いてつけ加えたり、取り去ったりした。奇怪な幻想的な城が、そのたびに赤くなったり青くなったりした。
　やっとそれはでき上がった。そして軽く跳りあがる心を制しながら、その城壁の頂きに恐る恐る檸檬れもんを据えつけた。そしてそれは上出来だった。
　見わたすと、その檸檬の色彩はガチャガチャした色の階調をひっそりと紡錘形の身体の中へ吸収してしまって、カーンと冴えかえっていた。私は埃ほこりっぽい丸善の中の空気が、その檸檬の周囲だけ変に緊張しているような気がした。私はしばらくそれを眺めていた。
　不意に第二のアイディアが起こった。その奇妙なたくらみはむしろ私をぎょっとさせた。
　――それをそのままにしておいて私は、なに喰くわぬ顔をして外へ出る。――
　私は変にくすぐったい気持がした。「出て行こうかなあ。そうだ出て行こう」そして私はすたすた出て行った。
　変にくすぐったい気持が街の上の私を微笑ほほえませた。丸善の棚へ黄金色に輝く恐ろしい爆弾を仕掛けて来た奇怪な悪漢が私で、もう十分後にはあの丸善が美術の棚を中心として大爆発をするのだったらどんなにおもしろいだろう。
　私はこの想像を熱心に追求した。「そうしたらあの気詰まりな丸善も粉葉こっぱみじんだろう」
　そして私は活動写真の看板画が奇体な趣きで街を彩いろどっている京極を下って行った。"""

    chain = PrepareChain(text)
    triplet_freqs = chain.make_triplet_freqs()
    chain.save(triplet_freqs, True)
