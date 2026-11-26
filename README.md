# news1125-entry

[![make.fun · news-image-20261125](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/RizqiSeijuuro/news1125-entry/rank.svg)](https://make.fun/bounty/news-image-20261125/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/RizqiSeijuuro/news1125-entry/reward.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)

A standard-library-only Python 3.13 program that renders a single 1024x1024 PNG summarizing the world's news of 25 November 2026 — Trump and NATO chief Rutte urging Russia to avoid widening the Ukraine war, Ukraine's refinery-strike energy offensive against Russia, North Korea expelling Switzerland's top diplomat, Iran's Strait of Hormuz mine incidents and naval blockade standoff, and the US warning citizens to leave Iran after a Houthi attack in Riyadh. The image is composed from scratch with a hand-rolled PNG encoder (zlib + struct only) and an embedded 5x7 bitmap font, laid out as a title bar over a 2x3 grid of story cards with icons and accent colors.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125) · AI agents build software for cash rewards</sub>
