# LOTO6 出現傾向シミュレータ

過去のロト6抽選データから統計的傾向を分析し、出現期待度を可視化するWebアプリケーションです。

> **免責事項**: 本ツールは統計的傾向を可視化するシミュレータです。ロト6は毎回独立した完全ランダム抽選であり、過去のデータが将来の結果を保証するものではありません。

## 機能

- **自動データ収集**: 起動時 + 毎日22:00 JST に mk-mode.com から全履歴CSVを自動取得
- **期待度分析**: 各数字 (1-43) の出現頻度・未出間隔・直近トレンドから期待度スコアを算出
- **5口シミュレーション**: 重み付きサンプリング + フィットネス評価 + 多様化選抜で5口生成
- **ヒートマップ**: 5段階 (Lv1-Lv5) の色分けで期待度を可視化

## 技術スタック

- **Backend**: Python 3.11 / FastAPI / SQLite / APScheduler
- **Frontend**: Vanilla JS / Tailwind CSS (CDN)

## ローカル起動

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

ブラウザで http://localhost:8000 を開く

## デプロイ

### Render (推奨・無料枠あり)

1. GitHubリポジトリにプッシュ
2. [Render](https://render.com) でアカウント作成
3. **New > Web Service** → リポジトリを接続
4. `render.yaml` が自動検出され設定完了

### Docker

```bash
docker build -t loto6 .
docker run -p 8000:8000 loto6
```

### Heroku / Railway

`Procfile` が同梱されているのでそのまま使えます。

## API

| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/health` | ヘルスチェック |
| GET | `/api/status` | データ取得状況 |
| GET | `/api/latest` | 直近の当選番号 |
| GET | `/api/expectation` | 1-43 各数字のスコア・レベル |
| GET | `/api/predictions` | 5口分の組み合わせ |
| POST | `/api/refresh` | 手動データ再取得 |

## スコア算出

| 要素 | 重み | 説明 |
|------|------|------|
| freq | 40% | 通算出現頻度 (min-max正規化) |
| gap | 40% | 直近出現からの経過回数 |
| recent | 20% | 直近50回での出現回数 |

レベル配分 (上位傾斜): Lv5=3個 / Lv4=6個 / Lv3=10個 / Lv2=11個 / Lv1=13個
