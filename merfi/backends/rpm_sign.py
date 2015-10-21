import os
from tambo import Transport
import merfi
from merfi import logger
from merfi import util
from merfi.collector import RepoCollector
from merfi.backends import base


class RpmSign(base.BaseBackend):
    help_menu = 'rpm-sign handler for signing files'
    _help = """
Signs files with rpm-sign. Crawls a given path looking for 'Release' files (by
default)

%s

Options

--key         Name of the key to use (see rpm-sign --list-keys)
--keyfile     Full path location of the keyfile, defaults to
              /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release

Positional Arguments:

[path]        The path to crawl for signing release files. Defaults to current
              working directory
    """
    executable = 'rpm-sign'
    name = 'rpm-sign'
    options = ['--key']

    def clear_sign(self, path, command):
        """
        When doing a "clearsign" with rpm-sign, the output goes to stdout, so
        that needs to be captured and written to the default output file for
        clear signed signatures (InRelease).
        """
        logger.info('signing: %s' % path)
        out, err, code = util.run_output(command)
        absolute_directory = os.path.dirname(os.path.abspath(path))
        with open(os.path.join(absolute_directory, 'InRelease'), 'w') as f:
            f.write(out)

    def detached(self, command):
        return util.run(command)

    def sign(self):
        logger.info('Starting path collection, looking for files to sign')
        self.keyfile = self.parser.get('--keyfile', 'Release.gpg')
        self.key = self.parser.get('--key')
        if not self.key:
            raise RuntimeError('specify a --key for signing')
        repos = RepoCollector(self.path)
        paths = []
        for repo in repos:
            repo_paths = RepoCollector.debian_release_files(repo)
            paths.extend(repo_paths)

        if paths:
            logger.info('%s matching paths found' % len(paths))
            # FIXME: this should spit the actual verified command
            logger.info('will sign with the following commands:')
            logger.info('rpm-sign --key "%s" --detachsign Release --output Release.gpg' % self.key)
            logger.info('rpm-sign --key "%s" --clearsign Release --output InRelease' % self.key)
        else:
            logger.warning('No paths found that matched')

        for path in paths:
            if merfi.config.get('check'):
                new_gpg_path = path.split('Release')[0]+'Release.gpg'
                new_in_path = path.split('Release')[0]+'InRelease'
                logger.info('[CHECKMODE] signing: %s' % path)
                logger.info('[CHECKMODE] signed: %s' % new_gpg_path)
                logger.info('[CHECKMODE] signed: %s' % new_in_path)
            else:
                os.chdir(os.path.dirname(path))
                detached = ['rpm-sign', '--key', self.key, '--detachsign', 'Release', '--output', 'Release.gpg']
                clearsign = ['rpm-sign', '--key', self.key, '--clearsign', 'Release']
                logger.info('signing: %s' % path)
                self.detached(detached)
                self.clear_sign(path, clearsign)
