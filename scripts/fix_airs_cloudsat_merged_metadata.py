#!/usr/bin/env python
import os, sys, re, traceback, logging, requests, json, shutil, sqlite3
from subprocess import check_call
from urlparse import urlparse
import easywebdav

requests.packages.urllib3.disable_warnings()


log_format = "[%(asctime)s: %(levelname)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger('fix')


DAV_URL = "https://msas-dav.jpl.nasa.gov"
PROD_RE = re.compile(r'^/data/public(/.*)$')


def call(cmd, noraise=False):
    """Run command and warn if exit status is not 0."""

    try: check_call(cmd, shell=True)
    except Exception as e:
        if noraise:
            logger.warn("Got exception running {}: {}".format(cmd, str(e)))
            logger.warn("Traceback: {}".format(traceback.format_exc()))
        else: raise


def fix_file(nc_file):
    """Fix DOI and remove AIRS_DAP_URL."""

    call("/home/gmanipon/anaconda2/bin/ncatted --glb_att_add IDENTIFIER_PRODUCT_DOI=10.5067/MEASURES/WVCC/DATA205 -Oh %s" % nc_file)
    call("/home/gmanipon/anaconda2/bin/ncatted -a AIRS_DAP_URL,global,d,, -Oh %s" % nc_file)


def upload(path, url):
    """Upload file to webdav path."""

    parsed = urlparse(url)
    c = easywebdav.connect(parsed.hostname, username='', password='', protocol=parsed.scheme, verify_ssl=False)
    c.upload(path, parsed.path)


def main():
    # get db conn/cursor
    conn = sqlite3.connect('done.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS files (id TEXT)')

    root_dir = "/data/public/repository/products/wvcc/matched/airs.aqua_cloudsat/v4.0"
    for root, dirs, files in os.walk(root_dir):
        dirs.sort()
        files.sort()
        for file in files:
            # skip if not nc4 file
            if not file.endswith('.nc4'): continue

            # skip if already fixed
            c.execute('SELECT * FROM files WHERE id=?', (file,))
            res = c.fetchone()
            #print(res)
            if res is not None: continue

            # fix
            nc_file = os.path.join(root, file)
            #print(nc_file)
            tmp_file = os.path.join('/tmp', file)
            #print(tmp_file)
            shutil.copy(nc_file, tmp_file)
            fix_file(tmp_file)
            url = "%s%s" % (DAV_URL, PROD_RE.search(nc_file).group(1))
            #print(url)
            #call("ls -l %s" % nc_file)
            upload(tmp_file, url)

            # save fixed file
            c.execute("INSERT INTO files VALUES (?)", (file,))
            conn.commit()

            #call("ls -l %s" % nc_file)

            # cleanup tmp file
            os.unlink(tmp_file)

            #sys.exit()


if __name__ == "__main__":
    main()
