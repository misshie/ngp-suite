# 第三者ライセンス表示の追加（実装済み）

ブランチ: `feat/mount-gmdb-data`

## 確認した上流とライセンス（2026-10-04 に GitHub で原文を確認）

| 上流 | ライセンス | 対象 |
| --- | --- | --- |
| biubug6/Pytorch_Retinaface | MIT, Copyright (c) 2019 | `lib/models/net.py`, `lib/models/retinaface.py`, `lib/utils/box_utils.py`, `lib/utils/prior_box.py`, `lib/face_alignment.py`（検出部） |
| amdegroot/ssd.pytorch | MIT, Copyright (c) 2017 Max deGroot, Ellis Brown | `lib/utils/box_utils.py`（Pytorch_Retinaface 経由） |
| fmassa/object-detection.torch | BSD-2-Clause, Copyright (c) 2015 Francisco Massa | `box_utils.py` の `nms` |
| rbgirshick/py-faster-rcnn | MIT, Copyright (c) 2015 Microsoft Corporation | `lib/utils/py_cpu_nms.py` |
| deepinsight/insightface | MIT（README に記載。LICENSE ファイルは無い） | `lib/face_alignment.py`（`arcface_src`, `estimate_norm`） |

## 未解決の点

- `box_utils.py` の `decode` には "Adapted from Hakuyume/chainer-ssd" とある。しかし chainer-ssd にはライセンス表記が無い。
- このコードは ssd.pytorch（MIT）→ Pytorch_Retinaface（MIT）の経路で取り込まれたもの。数行の数式実装であり、NOTICES にこの事実を明記した。
- 2026-10-04 決定: 書き直しや作者への確認は行わず、現状のまま残す（NOTICES に経緯を明記した状態を維持する）。

## 変更内容

- `backend/THIRD_PARTY_NOTICES.md` を新規作成した（著作権表示とライセンス全文）。モデル重みを同梱しないことと、insightface モデルが非商用の研究目的に限られることも明記した。
- `backend/lib` の上記6ファイルの冒頭に、出典コメントを追加した。ロジックは変更していない。
- `backend/Dockerfile` に次を追加した。
  - `LABEL org.opencontainers.image.licenses="CC-BY-NC-4.0"`
  - `COPY THIRD_PARTY_NOTICES.md`
  - ルートの `LICENSE.md` はビルドコンテキストの外にあるため、ラベルで示している。
- README.md と README-ja.md を更新した。
  - ライセンス節に、第三者コードの扱いを追記した。
  - 謝辞に Pytorch_Retinaface と InsightFace を追加した。
  - `README-be.md` は変更していない。

## 検証

- `docker compose build` は成功した。
- `/api/status` は 200 を返した。
- `/app/THIRD_PARTY_NOTICES.md` がイメージ内にあることを確認した。
- イメージのラベルは `CC-BY-NC-4.0` になっていることを確認した。

## 対象外（Docker Hub 公開時の別タスク）

- pip 依存の表示（torch、numpy、opencv-python-headless〔FFmpeg は LGPL〕など）
- Debian ベースイメージ（GPL パッケージを含む）
- `static/` に含まれる npm 資産（Vue、Vuetify、アイコンフォントなど）
