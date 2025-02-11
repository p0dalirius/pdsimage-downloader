#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File name          : pdsimage_downloader.py
# Author             : Podalirius (@podalirius_)
# Date created       : 2 Aug 2022

# to install requirements: python3 -m pip install requests bs4 lxml
import argparse
import sys
import requests
import os
from bs4 import BeautifulSoup
from rich import progress


# I'm disabling IPv6 since pdsimage2.wr.usgs.gov does not support it
requests.packages.urllib3.util.connection.HAS_IPV6 = False


def parseArgs():
    print("pdsimage downloader v1.1 - by Remi GASCOU (Podalirius)\n")
    parser = argparse.ArgumentParser(description="A python script to filter by filename and download PDS images.")
    parser.add_argument("-u", "--url", default=None, required=True, help='URL of the PDS image archive.')
    parser.add_argument("-n", "--name-contains", default='', type=str, help='Filtering only files where the name contains this string.')
    parser.add_argument("-D", "--output-dir", default="."+os.path.sep+"pdsimages_downloaded"+os.path.sep, help='Output directory where the images will be stored.')
    parser.add_argument("-v", "--verbose", default=False, action="store_true", help='Verbose mode. (default: False)')
    return parser.parse_args()


def yesno_question(msg):
    msg = msg + " (y/N) "
    response = input(msg).strip().lower()
    while response not in ['y', 'Y', 'n', 'N']:
        print("[!] Invalid choice. Please answer 'yes' or 'no'.")
        response = input(msg).strip().lower()

    if response in ['y', 'yes']:
        return True
    elif response in ['n', 'no']:
        return False



def extract_pdsdata_links(url):
    """
    Gets all the possible links to files from a pdsimage archive link
    :param url:
    :return: dict
    """
    pdsdata = {}
    print("[>] Sending request ... ", end="")
    sys.stdout.flush()
    r = requests.get(url, timeout=60*5)
    print("got response!")
    soup = BeautifulSoup(r.content, 'lxml')
    for a in soup.findAll('a'):
        if a['href'] in ["../", "./"]:
            continue

        if a['href'].startswith('/'):
            baseurl = '/'.join(url.split('/')[:3]) + '/'
            link = baseurl + a['href']
        else:
            link = url + a['href']

        filename = link.split('/')[-1]
        extension = filename.split('.')[-1]

        if filename not in pdsdata.keys():
            pdsdata[filename] = {}
        pdsdata[filename][extension] = link
    return pdsdata


def download_file(download_dir, download_url, filename, verbose=False):
    filename = download_url.split('/')[-1]
    r = requests.head(download_url, allow_redirects=True)
    if r.status_code == 200:
        target_file = download_dir + os.path.sep + filename
        with progress.Progress() as p:
            progress_bar, csize = p.add_task("[cyan]Downloading %s" % filename, total=int(r.headers["Content-Length"])), 1024*16
            pdb = requests.get(r.url, headers={"User-Agent": "Microsoft-Symbol-Server/10.0.10036.206"}, stream=True)
            with open(target_file, "wb") as f:
                for chunk in pdb.iter_content(chunk_size=csize):
                    f.write(chunk)
                    p.update(progress_bar, advance=len(chunk))
    else:
        print("[!] (HTTP %d) Could not find %s " % (r.status_code, download_url))


if __name__ == '__main__':
    options = parseArgs()

    # Parsing page
    pdsdata = extract_pdsdata_links(options.url)

    print("[+] Detected %d PDS image files (couple of LBL and IMG)" % len(pdsdata.keys()))

    # Creating the output dir if it exists
    if not os.path.exists(options.output_dir):
        os.makedirs(options.output_dir, exist_ok=True)

    # Filtering and downloading only what you need:
    keep_for_download = {}
    number_of_files = 0
    for filename, filelinks in pdsdata.items():
        if options.name_contains in filename:
            if options.verbose:
                print("[debug] Keeping '%s' for download." % filename)
            keep_for_download[filename] = filelinks
            number_of_files += len(filelinks.keys())
        else:
            if options.verbose:
                print("[debug] Ignoring '%s' for download." % filename)

    if yesno_question("[?] Filter on filenames containing '%s' returned %d files. Download them ?" % (options.name_contains, number_of_files)):
        # Download the selected files
        for filename, filelinks in keep_for_download.items():
            for extension in filelinks.keys():
                download_file(options.output_dir, filelinks[extension], filename)
        print("[+] Downloaded %d files!" % number_of_files)
    else:
        print("[!] Download aborted.")
