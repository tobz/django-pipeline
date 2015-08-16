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


class ClosureCompressor(SubProcessCompressor):

    def compress_js(self, js):
        command = '%s %s' % (settings.PIPELINE_CLOSURE_BINARY, settings.PIPELINE_CLOSURE_ARGUMENTS)
        return self.execute_command(command, js)

    def compress_js_with_source_map(self, paths):
        args = re.split(r'\s+', settings.PIPELINE_CLOSURE_BINARY)
        if settings.PIPELINE_CLOSURE_ARGUMENTS:
            if isinstance(settings.PIPELINE_CLOSURE_ARGUMENTS, six.string_types):
                args += shlex.split(settings.PIPELINE_CLOSURE_ARGUMENTS)
            else:
                args += settings.PIPELINE_CLOSURE_ARGUMENTS
        abs_paths = []
        for path in paths:
            abs_path = staticfiles_storage.path(path)
            args += [
                '--source_map_location_mapping',
                "%s|%s" % (abs_path, staticfiles_storage.url(path))]
            abs_paths.append(abs_path)
            with open(abs_path) as f:
                content = f.read()
            matches = source_map_re.search(content)
            if matches:
                input_source_map = filter(None, matches.groups())[0]
                input_source_map_file = os.path.join(os.path.dirname(abs_path), input_source_map)
                args += [
                    '--source_map_input',
                    "%s|%s" %  (abs_path, input_source_map_file)]

        temp_file = tempfile.NamedTemporaryFile()

        args += ["--create_source_map", temp_file.name]
        for path in abs_paths:
            args += ["--js", path]

        js = self.execute_command(args, None, shell=False)

        with open(temp_file.name) as f:
            source_map = f.read()

        temp_file.close()

        return js, source_map
