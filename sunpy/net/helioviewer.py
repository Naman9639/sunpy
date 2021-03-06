"""
This module provides a wrapper around the Helioviewer API.
"""
from __future__ import absolute_import

# pylint: disable=E1101,F0401,W0231

__author__ = ["Keith Hughitt"]
__email__ = "keith.hughitt@nasa.gov"

import os
import errno
import json
import codecs
import sunpy
from sunpy.time import parse_time
from sunpy.util.net import download_fileobj

from sunpy.extern.six.moves import urllib

__all__ = ['HelioviewerClient']


class HelioviewerClient(object):
    """Helioviewer.org Client"""
    def __init__(self, url="https://api.helioviewer.org/"):
        """
        url : location of the Helioviewer API.  The default location points to
            version 2 of the API.
        """
        self._api = url

    def get_data_sources(self):
        """
        Returns a structured list of datasources available at helioviewer.org.
        """
        params = {"action": "getDataSources"}

        return self._get_json(params)

    def get_closest_image(self, date, sourceId):
        """Finds the closest image available for the specified source and date.

        For more information on what types of requests are available and the
        expected usage for the response, consult the Helioviewer API
        documentation: http://api.helioviewer.org/docs/v2/ .

        Parameters
        ----------
        date : `datetime.datetime`, `str`
            A string or datetime object for the desired date of the image
        sourceId : int
            It is a unique number that can be used to refer a particular image
            datasource in the API reqeust.

        Returns
        -------
        out : `dict`
            A dictionary containing meta-information for the closest image matched

        Examples
        --------
        >>> from sunpy.net import helioviewer
        >>> client = helioviewer.HelioviewerClient()  # doctest: +REMOTE_DATA
        >>> metadata = client.get_closest_image('2012/01/01', sourceId=11)  # doctest: +REMOTE_DATA
        >>> print(metadata['date'])  # doctest: +REMOTE_DATA
        2012-01-01 00:00:07
        """
        params = {
            "action": "getClosestImage",
            "date": self._format_date(date),
            "sourceId": sourceId
        }

        response = self._get_json(params)

        # Cast date string to DateTime
        response['date'] = parse_time(response['date'])

        return response

    def download_jp2(self, date, sourceId, directory=None, overwrite=False, **kwargs):
        """
        Downloads the JPEG 2000 that most closely matches the specified time and
        data source.

        The data source may be specified either using it's sourceId from the
        get_data_sources query, or a combination of observatory, instrument,
        detector and measurement.

        Parameters
        ----------
        date : `datetime.datetime`, string
            A string or datetime object for the desired date of the image
        sourceId : int
            It is a unique number that can be used to refer a particular image
            datasource in the API reqeust.
        jpip : bool
            (Optional) Returns a JPIP URI if set to True
        json : bool
            (Optional) Returns a JSON object if set to True

        Returns
        -------
        out : string
            Returns a filepath to the downloaded JPEG 2000 image or a URL if
            the "jpip" parameter is set to True.

        Examples
        --------
        >>> import sunpy.map
        >>> from sunpy.net import helioviewer
        >>> hv = helioviewer.HelioviewerClient()  # doctest: +REMOTE_DATA
        >>> data_sources = hv.get_data_sources()  # doctest: +REMOTE_DATA
        >>> file = hv.download_jp2('2012/07/03 14:30:00', sourceId=data_sources['SOHO']['LASCO']['C2']['white-light']['sourceId'])   # doctest: +REMOTE_DATA
        >>> aia = sunpy.map.Map(file)   # doctest: +REMOTE_DATA
        >>> aia.peek()   # doctest: +SKIP
        """
        params = {
            "action": "getJP2Image",
            "date": self._format_date(date),
            "sourceId": sourceId
        }
    
        params.update(kwargs)

        # JPIP URL response
        if 'jpip' in kwargs:
            return self._get_json(params)

        return self._get_file(params, directory, overwrite=overwrite)

    def download_png(self, date, image_scale, layers, eventLabels=False, directory=None,
                     overwrite=False, **kwargs):
        """Downloads a PNG image using data from Helioviewer.org. It uses the
        takeScreenshot function from the API to perform this task.

        Returns a single image containing all layers/image types requested.
        If an image is not available for the date requested the closest
        available image is returned. The region to be included in the
        image may be specified using either the top-left and bottom-right
        coordinates in arc-seconds, or a center point in arc-seconds and a
        width and height in pixels. See the Helioviewer.org API Coordinates
        Appendix for more information about working with coordinates in
        Helioviewer.org.

        Parameters
        ----------
        date : `datetime.datetime`, string
            A string or datetime object for the desired date of the image
        image_scale : float
            The zoom scale of the image. Default scales that can be used are
            0.6, 1.2, 2.4, and so on, increasing or decreasing by a factor
            of 2. The full-res scale of an AIA image is 0.6.
        layers : string
            Image datasource layer/layers to include in the screeshot.
            Each layer string is comma-separated with these values, e.g.:
            "[sourceId,visible,opacity]" or "[obs,inst,det,meas,visible,opacity]"
            Multiple layer string are by commas: "[layer1],[layer2],[layer3]"
        eventLabels : bool
            Optionally annotate each event marker with a text label.
        events : string
            (Optional)  List feature/event types and FRMs to use to annoate the 
            movie. Use the empty string to indicate that no feature/event annotations 
            should be shown e.g.: [AR,HMI_HARP;SPoCA,1],[CH,all,1]
        scale : bool
            (Optional) Optionally overlay an image scale indicator.
        scaleType : string
            (Optional) Image scale indicator.
        scaleX : number
            (Optional) Horizontal offset of the image scale indicator in arcseconds with respect 
            to the center of the Sun.
        scaleY : number
            (Optional) Vertical offset of the image scale indicator in arcseconds with respect 
            to the center of the Sun.
        x1 : float
            (Optional) The offset of the image's left boundary from the center
            of the sun, in arcseconds.
        y1 : float
            (Optional) The offset of the image's top boundary from the center
            of the sun, in arcseconds.
        x2 : float
            (Optional) The offset of the image's right boundary from the
            center of the sun, in arcseconds.
        y2 : float
            (Optional) The offset of the image's bottom boundary from the
            center of the sun, in arcseconds.
        x0 : float
            (Optional) The horizontal offset from the center of the Sun.
        y0 : float
            (Optional) The vertical offset from the center of the Sun.
        width : int
            (Optional) Width of the image in pixels (Maximum: 1920).
        height : int
            (Optional) Height of the image in pixels (Maximum: 1200).
        watermark : bool
            (Optional) Optionally overlay a watermark consisting of a
            Helioviewer logo and the datasource abbreviation(s) and
            timestamp(s) displayed in the screenshot.
        display : bool
            (Optional) Set to `true` to directly output binary PNG image data.
            Default is `false` (which outputs a JSON object).
        callback : string
            (Optional) Wrap the response object in a function call of your choosing.



        Returns
        -------
        out : string
            filepath to the PNG image

        Examples
        --------
        >>> from sunpy.net.helioviewer import HelioviewerClient
        >>> import datetime
        >>> hv = HelioviewerClient()  # doctest: +REMOTE_DATA
        >>> file = hv.download_png('2012/07/16 10:08:00', 2.4, "[SDO,AIA,AIA,171,1,100]", False, x0=0, y0=0, width=1024, height=1024)   # doctest: +REMOTE_DATA
        >>> file = hv.download_png('2012/07/16 10:08:00', 4.8, "[SDO,AIA,AIA,171,1,100],[SOHO,LASCO,C2,white-light,1,100]", True, x1=-2800, x2=2800, y1=-2800, y2=2800)   # doctest: +REMOTE_DATA
        """
        params = {
            "action": "takeScreenshot",
            "date": self._format_date(date),
            "imageScale": image_scale,
            "layers": layers,
            "eventLabels": eventLabels,
            "display": True
        }

        params.update(kwargs)
        return self._get_file(params, directory, overwrite=overwrite)

    def is_online(self):
        """Returns True if Helioviewer is online and available."""
        try:
            self.get_data_sources()
        except urllib.error.URLError:
            return False

        return True

    def _get_json(self, params):
        """Returns a JSON result as a string"""
        reader = codecs.getreader("utf-8")
        response = self._request(params)
        return json.load(reader(response))

    def _get_file(self, params, directory=None, overwrite=False):
        """Downloads a file and return the filepath to that file"""
        # Query Helioviewer.org
        if directory is None:
            directory = sunpy.config.get('downloads', 'download_dir')
        else:
            directory = os.path.abspath(os.path.expanduser(directory))

        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        response = self._request(params)
        try:
            filepath = download_fileobj(response, directory, overwrite=overwrite)
        finally:
            response.close()

        return filepath

    def _request(self, params):
        """Sends an API request and returns the result

        Parameters
        ----------
        params : `dict`
            Parameters to send

        Returns
        -------
        out : result of request
        """
        response = urllib.request.urlopen(
            self._api, urllib.parse.urlencode(params).encode('utf-8'))

        return response

    def _format_date(self, date):
        """Formats a date for Helioviewer API requests"""
        return parse_time(date).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + "Z"
