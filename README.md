# auto

Command-line client for [RANDOM.ORG](https://www.random.org/) true random integers.

Each run you specify **how many** numbers and the **inclusive range**. RANDOM.ORG generates the values from atmospheric noise. This tool does not let you pick or fake the output numbers.

## Usage

Python 3.9+; no extra packages.

Interactive (prompts for count / min / max each time):

```bash
python3 random_org.py
```

One-shot:

```bash
python3 random_org.py --num 5 --min 1 --max 100
```

Unique numbers (no duplicates):

```bash
python3 random_org.py --num 6 --min 1 --max 49 --unique
```

Check remaining bit quota:

```bash
python3 random_org.py --quota
```

Comma-separated output:

```bash
python3 random_org.py --num 3 --min 1 --max 10 --sep ','
```

Optional: set `RANDOM_ORG_EMAIL` so RANDOM.ORG can contact you if the client misbehaves (their automated-client guideline).

```bash
export RANDOM_ORG_EMAIL="you@example.com"
```

## 交给客户（不要只发 `.py`）

给客户一个可双击的程序，而不是源码：

1. 把本仓库推到 GitHub 后，打开 **Actions → Build client app**，下载对应系统的产物。
2. 或在本机打包：

```bash
bash scripts/build_client.sh
```

Windows 客户发给 `delivery/RandomNumberGenerator.exe` 和 `packaging/客户使用说明.txt`。
对方双击 exe，填写个数/范围后点「生成」即可。

本地预览界面：

```bash
python3 random_org_gui.py
```

可执行文件不是加密，只是客户不用安装 Python，也看不到平时的 `.py` 文件。Windows 可能提示“未识别的应用”，因为未做代码签名。

## Tests

```bash
python3 test_random_org.py
python3 test_random_org_gui.py
```
