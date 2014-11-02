#!/usr/bin/python
"""Generates an HTML page using a given HTML template and a content file.

The HTML template can contain any number of variables of the form %{varname} whose
value is specified in the given content file.  The content file can also contain
references to <galleria> element tags containing images and captions to be converted
into a Galleria div. See: http://galleria.io/
"""

import os
import re
import sys
import json

import argparse

import HTMLParser
import image_galleria

import csv
import cStringIO as c

from collections import defaultdict

class AttributeParser(HTMLParser.HTMLParser):
    content = ''
    attributes = ''

    def handle_starttag(self, tag, attrs):
        self.attributes = attrs
    def handle_data(self, data):
        self.content = data

def is_image(text):
    return re.search(r'\.(?:jpe?g|png|gif)(\s|$)', text)
    
def generate_gallery(args, galleria_html):
    opts = dict()
    js_opts = dict()
    known = set(['stage_width', 'stage_height', 'width', 'height', 'thumbheight', 'disable_keyboard_nav'])
    images = []
    captions = defaultdict(str)

    # Parse the html attributes of the <galleria> tag that control the
    # rendering of the image gallery
    ap = AttributeParser()
    ap.feed(galleria_html)
    for key, value in ap.attributes:
        if key in known:
            opts[key] = int(value)
        else:
            js_opts[key] = value

    # Parse out the images
    curimage = ''
    for line in ap.content.split('\n'):
        line = line.strip()

        # Split the line on spaces, looking for images
        if is_image(line):
            for split in csv.reader(c.StringIO(line), delimiter=' ', escapechar='\\').next():
                if is_image(split):
                    images.append(split)
                    curimage = split
        else:
            captions[curimage] += line

    return image_galleria.generate(images, captions, no_cache=args.no_cache, 
                                    outputdir=args.outputdir, js_opts=js_opts, **opts)

def create(args):

    expansions = defaultdict(str)

    # Read in content file, parsing each of the substitutions
    with open(args.content_file, 'r') as infile:
        for line in infile.readlines():
            m = re.search(r'^\[(.*?)\]:(.*)', line)
            if m:
                key = m.group(1)
                expansions[key] = m.group(2)
            else:
                expansions[key] += line

    # Read in the html file
    with open(args.template_file, 'r') as infile:
        html = infile.read()

    # Expand all substitutions
    m = re.findall(r'(\%\{(.*?)\})', html)
    for pattern, name in m:
        html = re.sub(pattern, expansions[name], html)

    # Create and substitute the image galleries
    m = re.findall(r'(<galleria.*?</galleria>)', html, re.S)
    for content in m:
        html = re.sub(content, generate_gallery(args, content), html)

    # Save the html
    with open(os.path.join(args.outputdir, args.outputfile), 'w') as outfile:
        outfile.write(html)

def main():
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('template_file',
                        help='the html template file to expand into the resulting html file')
    parser.add_argument('content_file', 
                        help='the content file containing the template definitions')
    parser.add_argument('--outputdir', default='.',
                        help='where to save the index.html and scaled images')
    parser.add_argument('--outputfile', default='index.html',
                        help='the name of the expanded HTML file (defaults to index.html)')
    parser.add_argument('--no-cache', dest='no_cache', action='store_true',
                        help='scale images even if they already exist')

    create(parser.parse_args())



if __name__ == "__main__":
    main()

