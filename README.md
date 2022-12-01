![GitHub](https://img.shields.io/github/license/LaGGgggg/from-site-to-infopath-parser?label=License)
![GitHub watchers](https://img.shields.io/github/watchers/LaGGgggg/from-site-to-infopath-parser)
![GitHub last commit](https://img.shields.io/github/last-commit/LaGGgggg/from-site-to-infopath-parser)
[![wakatime](https://wakatime.com/badge/user/824414bb-4135-4fbc-abbd-0d007987e855/project/64a766b2-0a70-4e56-bd10-590a93fad061.svg)](https://wakatime.com/badge/user/824414bb-4135-4fbc-abbd-0d007987e855/project/64a766b2-0a70-4e56-bd10-590a93fad061)

---

# From site to infopath parser

It's a simple parser, that can parse data from two websites (you can choose which one) and
saves it in the infopath xml file. The parser has a GUI and logging,
can save data to a new file and parse different data from one site (more on that later).

---

## Quick start

### 1. Copy repository:
```bash
git clone https://github.com/LaGGgggg/from-site-to-infopath-parser.git
cd from-site-to-infopath-parser
```

### 2. Download [chrome driver](https://chromedriver.chromium.org/downloads):

### 3. Create the virtualenv:

#### With [pipenv](https://pipenv.pypa.io/en/latest/):

```bash
pip install --user pipenv
pipenv shell  # create and activate
```

#### Or classic:

```bash
python -m venv .venv  # create
.venv\Scripts\activate.bat   # activate
```

### 4. Install python packages

```bash
pip install -r requirements.txt
```

### 5. Environment variables:

There are three .env files in the project. One main and two for each of the sites.
To change the site being parsed, change the key in the main '.env' file.
(keys: 'sdo-vot', 'vmig.expert')

The project includes all .env files with launch settings, excluding login, password,
start page (link, where the parsing starts) and the topic of the questions
(a cosmetic variable for the result file field).

You should set all environment variables in the two .env files you use.

### 6. Run main .py file

```bash
python parser.py
```

---

## Result

To view the result file, you need to copy the 'curs.xsn' file to the root of the 'C' drive.
(example result: 'C://curs.xsn')

---

## Logging

The project has a logging system, a console inside a GUI.

---

## Authors
[LaGGgggg](https://github.com/LaGGgggg)

---

## [LICENSE](LICENSE)
