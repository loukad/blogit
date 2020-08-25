import os
import re
import sys
import json
import uuid
import exifread

import argparse

from fractions import Fraction

def resize_image(image, dest, no_cache, size_str):
    """Resizes the given image using ImageMagick convert utility.

    Args:
        image: the source image file name
        dest: the destination image file name
        no_cache: if true, resizes image even if destination image exists, else no op
        size_str: the target width-height ImageMagick format string
    Returns:
        None
    """

    # Don't reconvert files that exist
    if os.path.isfile(dest) and not no_cache:
        return

    command = 'convert %s -resize %s %s' % (image, size_str, dest)
    print('Sizing image:', image, 'into:', dest)
    if os.system(command):
        print('Could not convert image', image)
        sys.exit(1)

def get_exif_info(image):
    """ Returns an EXIF string with a few key attributes from the given image. """
    f = open(image, 'rb')
    tags = exifread.process_file(f)
    f.close()

    exif_line = []
    for tag, value in tags.iteritems():
        if tag == 'EXIF ExposureTime':
            shutter = str(value)
            m = re.search(r'(\d+)\/(\d+)', shutter)
            if m and int(m.group(1)) > int(m.group(2)):
                shutter = str(float(Fraction(shutter)))
            exif_line.append(shutter + ' s')
        elif tag == 'EXIF FNumber':
            aperture = str(value)
            if '/' in aperture:
                aperture = str(float(Fraction(aperture)))
            exif_line.append('f/' + aperture)
        elif tag == 'EXIF FocalLength':
            exif_line.append(str(value) + 'mm')
        elif 'EXIF ISO' in tag:
            exif_line.append('ISO ' + str(value))

    return ' | '.join(exif_line)

def generate(images, captions=dict(), outputdir='.', no_cache=False,
                stage_width=1080, stage_height=680,
                width=1200, height=800, thumbheight=50,
                disable_keyboard_nav=0, image_margin=0,
                toggleinfo=True, thumbnails=True,
                exif_class='isobar', js_opts=dict()):
    """ Generates a Galleria image gallery and returns the resulting HTML block.

        Args:
            images: the list of images (filenames) to use for the gallery
            captions: a dict of image name to description (optional)
            outputdir: the directory to store the scaled images (defaults to .)
            no_cache: generate resized images and thumbnails even if they exist
            stage_width: the width of the Galleria div
            stage_height: the height of the Galleria div
            width: the max width of the scaled images
            height: the max height of the scaled images
            thumbheight: the height of the thumbnail images (width is automatic)
            image_margin: how much space to put between the images and the stage
            exif_class: the CSS class to use for the EXIF text <span> element
            js_opts: a dict of Galleria javascript options
        Returns:
            the HTML of the Galleria div
    """

    for type in ['images', 'thumbs']:
        path = outputdir + '/' + type
        if not os.path.exists(path):
            os.makedirs(path)

    image_list = []
    image_sizes = { 'images': '%dX%d' % (width, height), 'thumbs': 'X%d' % thumbheight }

    for image in images:
        mapping = dict()
        name = os.path.basename(image)
        exif_info_line = get_exif_info(image)
        if len(exif_info_line) > 0:
            caption = captions[image] + '<br/>' if image in captions else ''
            mapping['description'] = caption + "<span class='" + exif_class + "'>" + \
                                     exif_info_line + "</span>"

        # Resize the images and thumbnails
        for type in ['images', 'thumbs']:
            mapping[type.strip('s')] = type + '/' + name
            dest = outputdir + '/' + mapping[type.strip('s')]

            resize_image(image, dest, no_cache, image_sizes[type])

        image_list.append(mapping)

    # Get out a unique id for this galeria object
    gallery_id = str(uuid.uuid1()).split('-')[0]

    # Set up the default galleria options
    galleria_opts = { 'lightbox' : False, 'showImagenav' : False,
                      'transitionSpeed' : 450, 'dataSource' : image_list,
                      'preload' : 'all',
                      '_toggleInfo' : toggleinfo,
                      'showInfo' : toggleinfo,
                      'thumbnails' : thumbnails,
                      'width' : stage_width, 'height' : stage_height,
                      'imageMargin' : image_margin,  }

    # Add any additional options or overrides
    for key, value in js_opts.iteritems():
        galleria_opts[key] = value

    navigation_code = "" if disable_keyboard_nav else """
            Galleria.ready(function() {
                this.attachKeyboard({
                    right: this.next,
                    left: this.prev
                });
            });
        """
    html = """
        <div align="center" id="%s"> </div>
        <script>
            Galleria.loadTheme('http://nablizo.com/galleria/themes/classic/galleria.classic.js');
            $('#%s').galleria(%s);
            %s
        </script>
        """ % (gallery_id,  gallery_id, json.dumps(galleria_opts), navigation_code)

    return html

