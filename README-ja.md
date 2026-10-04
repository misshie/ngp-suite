# **NGPsuite**

*This is a Japanese translation of [README.md](README.md). The English README.md is the original.*

*Next-Generation Phenotyping powered by GestaltMatcher and PubCaseFinder*

<img src="./assets/NGPsuite.png" width="85%" alt="NGP suite" />

## **目次**

1. [はじめに](#はじめに)
2. [エンドユーザー向け（インストールと利用）](#エンドユーザー向けインストールと利用)
3. [開発者向け](#開発者向け)
4. [技術スタック](#技術スタック)
5. [ライセンス](#ライセンス)
6. [謝辞](#謝辞)
7. [著者](#著者)
8. [参考文献](#参考文献)

----

<p align="center">
  <img src="./assets/ngpsuite-ss1.png" width="30%" alt="NGPsuite screenshot 1" />
  <img src="./assets/ngpsuite-ss2.png" width="30%" alt="NGPsuite screenshot 2" />
  <img src="./assets/ngpsuite-ss3.png" width="30%" alt="NGPsuite screenshot 3" />
</p>
<p align="center"><em>画像提供: Dr. Ibrahim Abdelrazek / GestaltMatcher Database https://db.gestaltmatcher.org/patients/15727</em></p>

----
## **はじめに**

**NGPsuite** は、稀少疾患の診断を支援する Web アプリケーションです。
画像から得られる顔貌表現型の解析と、臨床情報（HPO ID）を統合し、
臨床遺伝医や医学研究者に総合的な視点を提供します。

本アプリケーションは、画像ベースの予測に [GestaltMatcher](https://www.gestaltmatcher.org/) の解析力を用い、
さらに [PubCaseFinder](https://pubcasefinder.dbcls.jp/?lang=en) による HPO ベースの表現型解析を組み合わせることで、
次世代表現型解析（next-generation phenotyping）へのマルチモーダルなアプローチを実現します。

***NGPsuite、GestaltMatcher、PubCaseFinder、および外部情報源は、研究および教育目的のみを想定しています***。

----
## **エンドユーザー向け（インストールと利用）**

この節では、アプリケーションを実行したいユーザー向けの手順を説明します。
フロントエンドの開発環境は不要です。

### **前提条件**

* システムに Docker がインストールされていること。

### **1. アプリケーションの入手**

最新リリースの zip ファイルをダウンロードし、展開してください。

### **2. 必要なモデルとデータ**

倫理的な理由により、学習済みモデルは一般公開されていません。\
[GestaltMatcher Database (GMDB)](https://db.gestaltmatcher.org/) へのアクセスが許可された後、学習済みモデルの重みとアノテーションもリクエストできます。

> **破壊的変更:** Docker イメージには GMDB のモデル・ギャラリーエンコーディング・メタデータを含まなくなりました。
> これらはコンテナ起動時に、**お使いのマシン上のディレクトリから読み取り専用でマウント**されます。
> 患者由来のデータがイメージに入ることはなく、データを変更してもイメージの再ビルドは不要です。

GMDB のファイル用に、できればこのリポジトリの**外**（例: `~/ngpsuite-gmdb`）へ、`data/` と `saved_models/` の
サブディレクトリを持つディレクトリを作成してください。その場所は環境変数 `NGPSUITE_GMDB_DIR` で指定します
（手順 3 を参照）。必要なファイルを入手したら、次のとおり配置してください。

1. 事前学習済み特徴抽出（エンコーダ）モデル
次のファイルを `$NGPSUITE_GMDB_DIR/saved_models/` に配置します:
* `Resnet50_Final.pth`（顔アライメント用）
* `glint360k_r100.onnx`（モデル b 用のベース事前学習モデル。3 番目のエンコーダとしても使用）

2. 学習済み特徴空間モデル（ギャラリー）
次のファイルを `$NGPSUITE_GMDB_DIR/saved_models/` に配置します:
* `s1_glint360k_r50_512d_gmdb__v1.1.4_bs64_size112_channels3_last_model.pth`（モデル a）
* `s2_glint360k_r100_512d_gmdb__v1.1.4_bs128_size112_channels3_last_model.pth`（モデル b）

3. ギャラリーエンコーディング用アノテーション
次のファイルを `$NGPSUITE_GMDB_DIR/data/gallery_encodings/` に配置します:
* `GMDB_gallery_encodings_23052026_v1.1.4_service.pkl`

4. GestaltMatcher-Arc v1.1.4 用の追加データ
次のファイルを `$NGPSUITE_GMDB_DIR/data/` に配置します:
* `transformation_probabilities_07052025.csv`（PP4 用の症候群変換確率）
* `patient_metadata_2026-05-23_mondo.p`（疾患／遺伝子メタデータ。疾患は MONDO ID でキー付け）

上記 7 ファイルはすべて必須です。API は起動時にこれらを確認し、不足または読み取れないファイルがあれば、すべて列挙して直ちに停止します。

5. MONDO オントロジー（リポジトリ同梱）
次のファイルは `backend/mondo/` 配下で管理されており（患者データは含みません）、別途ダウンロードする必要はありません:
* `mondo-international.obo.gz`（ギャラリー疾患のラベルと祖先階層）

本製品には Mondo Disease Ontology (Mondo) の international edition（[mondo.monarchinitiative.org](https://mondo.monarchinitiative.org/)）が含まれます。Mondo のライセンスは [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) です。[謝辞](#謝辞)も参照してください。

最終的なファイル構成は次のようになります:

```
~/ngpsuite-gmdb/                 # = $NGPSUITE_GMDB_DIR（リポジトリ外。読み取り専用でマウントされる）
├── data/
│   ├── gallery_encodings/
│   │   └── GMDB_gallery_encodings_23052026_v1.1.4_service.pkl
│   ├── transformation_probabilities_07052025.csv
│   └── patient_metadata_2026-05-23_mondo.p
└── saved_models/
    ├── Resnet50_Final.pth
    ├── glint360k_r100.onnx
    ├── s1_glint360k_r50_512d_gmdb__v1.1.4_bs64_size112_channels3_last_model.pth
    └── s2_glint360k_r100_512d_gmdb__v1.1.4_bs128_size112_channels3_last_model.pth

ngp-suite/
└── backend/
    ├── mondo/                   # イメージに同梱
    │   └── mondo-international.obo.gz
    └── ... (その他のバックエンドファイル)
```

### **3. アプリケーションのビルドと実行**

backend ディレクトリに移動し、GMDB ファイルの場所を Docker Compose に伝えてから、サービスをビルドして起動します。

```
cd backend
cp .env.example .env          # .env を編集: NGPSUITE_GMDB_DIR=/absolute/path/to/ngpsuite-gmdb
                              # （認証情報と LAN 共有は任意。「5. 認証」を参照）
docker compose build          # コードのみのイメージをビルドします。GMDB データは含まれません
docker compose up -d          # `-d` を付けなければ、コンソールでログを確認できます。
```

（Linux で、ユーザーが `docker` グループに入っていない場合は、`docker` コマンドの前に `sudo` を付けてください。）

初回起動時は、API サービスがモデルを読み込むため、約 90 秒かかることがあります。
必須ファイルが不足している場合、`api` コンテナは直ちに終了し、不足しているファイルをすべて表示します
（`docker compose logs api`）。

モデルやデータを更新するときは、`$NGPSUITE_GMDB_DIR` 配下のファイルを差し替えて `docker compose restart api` を実行します。
再ビルドは不要です。

<details>
<summary><strong>v0.2.0 以前（データをイメージに焼き込む方式）からの移行</strong></summary>

以前のバージョンでは、ビルド時に `backend/data/` と `backend/saved_models/` が必要で、イメージにコピーされていました。
次のいずれかを選んでください。

* **推奨:** `backend/data/` と `backend/saved_models/` をリポジトリ外のディレクトリ（例: `~/ngpsuite-gmdb`）へ移し、`backend/.env` の `NGPSUITE_GMDB_DIR` にそのパスを設定します。
* **現在の配置のまま使う:** ファイルを `backend/data/` と `backend/saved_models/` に置いたままにし、`backend/.env` は作成しません。`NGPSUITE_GMDB_DIR` の既定値は `backend/` になります。

その後、一度だけ再ビルドしてください。古いイメージとビルドキャッシュには GMDB ファイルが残っているため、削除します。

```
docker compose down
docker image rm backend-api:latest
docker builder prune
```

</details>

#### **GPU / CUDA に関する注意**

NGPsuite（Web API）の Docker デプロイは **CPU** 上で動作します。ホストに GPU があっても、推論には GPU を使いません。エンドユーザーは CUDA、NVIDIA ドライバ、その他の GPU 関連セットアップを必要としません。

<details>
<summary><strong>開発者向け: 任意の CUDA 対応イメージビルド</strong></summary>

既定では、API イメージは **CPU 専用** の PyTorch をインストールします（イメージが小さく、NVIDIA パッケージ依存がありません）。

意図的にイメージ内へ CUDA 対応の PyTorch を入れたい場合（実験や将来の GPU 利用向け）は、次のようにビルドします:

```
cd backend
docker compose build --build-arg USE_CUDA=1
# 任意: キャッシュなしで再ビルドする場合
# docker compose build --no-cache --build-arg USE_CUDA=1
```

注意事項:

* 変更されるのはインストールされる PyTorch の wheel のみです。アプリケーションコードを CUDA 利用に変更しない限り、現行の Web API は CPU で推論します。
* CUDA ビルドはサイズが大きく、時間がかかり、`pip install` 時により多くのディスク容量を必要とします。
* 実行時に GPU を使うには、別途ホスト側に NVIDIA ドライバと NVIDIA Container Toolkit が必要です。これは本ビルドフラグとは独立です。

要件ファイル:

* `backend/requirements_docker.txt` — 既定（CPU）ビルド用の共通依存。PyTorch / torchvision は Dockerfile 内で公式の CPU wheel インデックスからインストールされます
* `backend/requirements_docker_cuda.txt` — 同じ依存に加え、CUDA オプトインビルド用の `torch`

Dockerfile は `torch==2.3.1` と `torchvision==0.18.1` を pip の constraints ファイルで固定し、他パッケージが PyPI から CUDA ビルドへ上げないようにしています。

</details>

### **4. アプリケーションへのアクセス**

起動が完了したら、Web ブラウザで次の URL を開いてください:  
`https://localhost`

#### **初回アクセス時のセキュリティ警告**

*NGPsuite* に初めてアクセスすると、自己署名証明書の使用により、ブラウザがセキュリティ警告を表示することがあります。これは想定どおりの動作です。続行するには、「詳細設定」や「続行…」などのボタンをクリックし、証明書を受け入れてください。

### **5. 認証**

`POST /api/predict` は HTTP Basic 認証で保護されています。初期状態の認証情報はプレースホルダの
`your_username` / `your_password` で、Web UI の既定値と同じため、設定なしで動作します。
これらの値は公開されているので、**プレースホルダには実質的な保護効果はありません**。
自分のマシンからしか届かない状態であれば問題ありません。既定ではポート 443 は `127.0.0.1` に公開されます。
プレースホルダを使っている間は、起動時に `api` コンテナが注意を表示します（`docker compose logs api`）。

本サービスは自分のマシンまたは信頼できる LAN 内での利用を想定しています。インターネットには公開しないでください。

**認証情報の変更。** `backend/.env` に設定し、`docker compose up -d` で反映します。

```
NGPSUITE_USERNAME=your-name
NGPSUITE_PASSWORD=a-long-password
```

Web UI の **Settings** にも同じ値を入力してください。認証情報は環境変数としてコンテナに渡され、イメージには保存されません。

**LAN での共有。** `backend/.env` に `NGPSUITE_BIND=0.0.0.0` を設定し、`docker compose up -d` を実行します。
`/api/predict` の応答には GMDB の患者に由来する情報が含まれるため、先に認証情報を変更してください。
プレースホルダのまま共有すると、`api` のログに目立つ警告が出ます（サービスは起動します）。

<details>
<summary><strong>前のリリースからの移行（config.json、ポート 443）</strong></summary>

* `backend/config.json` は使われなくなり、同梱もされません。値を変更していた場合は、`backend/.env` の
  `NGPSUITE_USERNAME` / `NGPSUITE_PASSWORD` に移し、一度だけ再ビルドしてください（`docker compose build`）。
* ポート 443 は `127.0.0.1` のみに公開されるようになりました。LAN 内の他のマシンから接続していた場合は、
  `backend/.env` に `NGPSUITE_BIND=0.0.0.0` を設定してください。

</details>

## **開発者向け**

この節は、プロジェクトへの貢献を希望する開発者向けです。

### **初期セットアップ**

1. **フロントエンド依存関係:**
```
   cd frontend  
   npm install
```

2. バックエンドデータ:  
   「エンドユーザー向け」節の手順 2・3 に従い、GMDB ファイルを任意のディレクトリに配置し、
   `backend/.env` の `NGPSUITE_GMDB_DIR` にそのパスを設定してください。ファイルはコンテナにコピーされず、マウントされます。

### **開発モードでの実行**

1. **フロントエンド開発サーバの起動:**
```
   cd frontend  
   npm run dev
```

2. バックエンド API サーバの起動:  
```
   別ターミナルで:  
   cd backend  
   docker compose up --build
```

   フロントエンドはホットリロード有効で `http://localhost:3000` から利用でき、
   Docker 内で動作する API サーバと通信します。

### **フロントエンドのビルド**

本番用フロントエンドをビルドし、backend の static ディレクトリへコピーするには、
プロジェクトルートから次のスクリプトを実行します:

`./build-frontend.sh`

## **技術スタック**

* **Frontend:** [![Vue.js 3](https://img.shields.io/badge/Vue.js-3-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Pinia](https://img.shields.io/badge/pinia-%23F8E035.svg?style=for-the-badge&logo=pinia&logoColor=black)](https://pinia.vuejs.org/)
[![vue-i18n](https://img.shields.io/badge/vue--i18n-4FC08D?style=for-the-badge&logo=vue.js&logoColor=white)](https://github.com/intlify/vue-i18n-next)
[![Axios](https://img.shields.io/badge/Axios-5A29E4?style=for-the-badge&logo=axios&logoColor=white)](https://github.com/axios/axios)
[![Vuetify](https://img.shields.io/badge/Vuetify-1867C0?style=for-the-badge&logo=vuetify&logoColor=white)](https://vuetifyjs.com/)
[![FilePond](https://img.shields.io/badge/FilePond-000000?style=for-the-badge&logo=filepond&logoColor=white)](https://pqina.nl/filepond/)
* **Backend:** [![Python 3](https://img.shields.io/badge/Python-3-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
* **Infrastructure:** [![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)](https://www.nginx.com/)

## **ライセンス**

[![Creative Commons License](https://i.creativecommons.org/l/by-nc/4.0/88x31.png)](http://creativecommons.org/licenses/by-nc/4.0/)


本プロジェクトは **Creative Commons Attribution-NonCommercial 4.0 International License** の下で提供されています。
詳細は [LICENSE.md](LICENSE.md) を参照してください。

## **謝辞**

本プロジェクトのバックエンドサービスは、
[GestaltMatcher](https://www.gestaltmatcher.org/) およびその [リポジトリ](https://github.com/igsb/GestaltMatcher-Arc/) の成果に基づいています。
バックエンドは PubCaseFinder の API も利用しています（[詳細](https://pubcasefinder.dbcls.jp/api)）。分野の基盤を築かれた皆様に感謝します。

本製品には Mondo Disease Ontology (Mondo) の international edition
（[mondo.monarchinitiative.org](https://mondo.monarchinitiative.org/)）が含まれます。Mondo のライセンスは
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) です。オントロジーファイルは `backend/mondo/` 配下に同梱されています。

本プロジェクトの開発に大きく寄与した貴重な議論と支援に対し、[DBCLS BioHackathon 2025](https://2025.biohackathon.org/)（2025年9月14–20日、三重、日本）および [DBCLS BioHackathon 2026](https://2026.biohackathon.org/)（2026年9月13–19日、愛媛、日本）の参加者および運営の皆様に感謝します。

## **著者**

* **Hiroyuki Mishima**（三嶋 博之）*
* 長崎大学原爆後障害医療研究所 人類遺伝学研究分野*
* [Research Map Profile](https://researchmap.jp/misshie?lang=en)

## 参考文献
### GestaltMatcher
1. **GestaltMatcher**: Hsieh, T.-C. et al. (2022). GestaltMatcher facilitates rare disease matching using facial phenotype descriptors. Nature Genetics, 54(3), 349-357. [https://www.nature.com/articles/s41588-021-01010-x](https://www.nature.com/articles/s41588-021-01010-x)
2. **GestaltMatcher-Arc**: Hustinx, A. et al. (2023). Improving deep facial phenotyping for ultra-rare disorder verification using model ensembles. 2023 IEEE/CVF Winter Conference on Applications of Computer Vision (WACV). doi:[10.1109/wacv56688.2023.00499](https://openaccess.thecvf.com/content/WACV2023/papers/Hustinx_Improving_Deep_Facial_Phenotyping_for_Ultra-Rare_Disorder_Verification_Using_Model_WACV_2023_paper.pdf)
3. **GestaltMatcher Database**: Lesmann, H. et al. (2024). GestaltMatcher Database - A global reference for facial phenotypic variability in rare human diseases. medRxiv. doi:[10.1101/2023.06.06.23290887](https://www.medrxiv.org/content/10.1101/2023.06.06.23290887v3)

### PubCaseFinder
1. Shin, J., Fujiwara, T., Saitsu, H., & Yamaguchi, A. (2025).Ontology-based expansion of virtual gene panels to improve diagnostic efficiency for rare genetic diseases. BMC medical informatics and decision making, 25(Suppl 1), 59. doi:[10.1186/s12911-025-02910-2](https://doi.org/10.1186/s12911-025-02910-2)
2. Fujiwara, T., Shin, J. M., & Yamaguchi, A. (2022). Advances in the development of PubCaseFinder, including the new application programming interface and matching algorithm. Human mutation, 10.1002/humu.24341. Advance online publication. doi:[10.1002/humu.24341](https://doi.org/10.1002/humu.24341)
3. Yamaguchi, A., Shin, J. M., & Fujiwara, T. (2021, December). Gene Ranking based on Paths from Phenotypes to Genes on Knowledge Graph. In The 10th International Joint Conference on Knowledge Graphs (pp. 131-134). doi:[10.1145/3502223.3502240](https://doi.org/10.1145/3502223.3502240)
4. Fujiwara, T., Yamamoto, Y., Kim, J. D., Buske, O., & Takagi, T. (2018). PubCaseFinder: A case-report-based, phenotype-driven differential-diagnosis system for rare diseases. The American Journal of Human Genetics, 103(3), 389-399. doi:[10.1016/j.ajhg.2018.08.003](https://doi.org/10.1016/j.ajhg.2018.08.003)
