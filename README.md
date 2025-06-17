# This is an Electronic Document Management System based on the Mayan-EDMS project

**It was modified and extended to fit into the environment of a law firm.**

**Mayan-EDMS: <https://www.mayan-edms.com/>**

## Installation

### Required

: **Python 2.7**

The following steps show an installation on a Ubuntu 22.04 system:  
<br/>**Required packages**:  
python2-pip-whl nginx supervisor redis-server postgresql libpq-dev libjpeg-dev libmagic1 libpng-dev libreoffice libtiff-dev gcc ghostscript gnupg1 python2-dev python3-virtualenv tesseract-ocr poppler-utils memcached python2-setuptools-whl

**The project is using a postgresql database:**

sudo -u postgres createuser -P &lt;db_user&gt;

sudo -u postgres createdb -O &lt;db_user&gt; &lt;db_name&gt;

1\. mkdir &lt;project_directory&gt;

1\. cd &lt;project_directory&gt;

2\. git clone <https://github.com/Ben-useit/mayan-310.git> mayan

3\. virtualenv --python=/usr/bin/python2 venv

4\. source venv/bin/activate

5\. pip install -r mayan/requirements.txt

6\. Initial Setup:

MAYAN_DATABASE_ENGINE=django.db.backends.postgresql MAYAN_DATABASE_NAME=&lt;db_name&gt; MAYAN_DATABASE_PASSWORD=&lt;db_password&gt; MAYAN_DATABASE_USER=&lt;db_user&gt; MAYAN_DATABASE_HOST=127.0.0.1 MAYAN_MEDIA_ROOT="&lt;project_directory&gt;/media" &lt;project_directory&gt;/venv/bin/python &lt;project_directory&gt;/mayan/bin/mayan-edms.py initialsetup

7\. Collect Static Files:

MAYAN_DATABASE_ENGINE=django.db.backends.postgresql MAYAN_DATABASE_NAME=&lt;db_name&gt; MAYAN_DATABASE_PASSWORD=&lt;db_password&gt; MAYAN_DATABASE_USER=&lt;db_user&gt; MAYAN_DATABASE_HOST=127.0.0.1 MAYAN_MEDIA_ROOT="&lt;project_directory&gt;/media" &lt;project_directory&gt;/venv/bin/python &lt;project_directory&gt;/mayan/bin/mayan-edms.py collectstatic --noinput

8\. Run Server

MAYAN_DATABASE_ENGINE=django.db.backends.postgresql MAYAN_DATABASE_NAME=&lt;db_name&gt; MAYAN_DATABASE_PASSWORD=&lt;db_password&gt; MAYAN_DATABASE_USER=&lt;db_user&gt; MAYAN_DATABASE_HOST=127.0.0.1 MAYAN_MEDIA_ROOT="&lt;project_directory&gt;/media" &lt;project_directory&gt;/venv/bin/python &lt;project_directory&gt;/mayan/bin/mayan-edms.py runserver
