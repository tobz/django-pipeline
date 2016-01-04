from __future__ import unicode_literals

import os
import re
import shlex
import tempfile

from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils import six

from pipeline.conf import settings
from pipeline.compressors import SubProcessCompressor


source_map_re = re.compile((
    "(?:"
      "/\\*"
      "(?:\\s*\r?\n(?://)?)?"
      "(?:%(inner)s)"
      "\\s*"
      "\\*/"
      "|"
      "//(?:%(inner)s)"
    ")"
    "\\s*$") % {'inner': r"""[#@] sourceMappingURL=([^\s'"]*)"""})


class UglifyJSCompressor(SubProcessCompressor):
    def compress_js(self, js):
        command = '%s %s' % (settings.PIPELINE_UGLIFYJS_BINARY, settings.PIPELINE_UGLIFYJS_ARGUMENTS)
        if self.verbose:
            command += ' --verbose'
        return self.execute_command(command, js)

    def compress_js_with_source_map(self, paths):
        # Build a list of arguments to run, starting with the binary path and any
        # user-specified arguments/flags.
        args = re.split(r'\s+', settings.PIPELINE_UGLIFYJS_BINARY)
        if settings.PIPELINE_UGLIFYJS_ARGUMENTS:
            if isinstance(settings.PIPELINE_UGLIFYJS_ARGUMENTS, six.string_types):
                args += shlex.split(settings.PIPELINE_UGLIFYJS_ARGUMENTS)
            else:
                args += settings.PIPELINE_UGLIFYJS_ARGUMENTS

        # Get the absolute path to the paths we were passed.
        abs_paths = []
        for path in paths:
            abs_path = staticfiles_storage.path(path)
            abs_paths.append(abs_path)

        temp_file = tempfile.NamedTemporaryFile()

        args += ["--source-map", temp_file.name]
        args += ["--source-map-include-sources"]

        args += ["--"]
        for path in abs_paths:
            args += [path]

        js = self.execute_command(args, None, shell=False)

        with open(temp_file.name) as f:
            source_map = f.read()

        temp_file.close()

        return js, source_map
