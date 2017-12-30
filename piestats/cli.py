import redis
import os
import click
import time
from piestats.update import update_events
from piestats.update.retention import Retention
from piestats.config import Config
from piestats.keys import Keys
from piestats.web import init_app
from piestats.update.filemanager.local import LocalFileManager
from piestats.update.filemanager.ssh import SshFileManager
from piestats.update.filemanager.ftp import FtpFileManager


@click.command()
@click.option(
    '--config_path',
    '-c',
    help='Path to config yaml file.',
    default=lambda: os.getenv('PYSTATS_CONF'),
    type=click.Path(exists=True, dir_okay=False),
    required=True)
def run_update(config_path):
  '''
    Run updates. Pass me path to config file which contains settings for redis
    as well as which soldat servers to process data for.
  '''

  start = time.time()
  # Parse our config yaml file
  config = Config(config_path)

  r = redis.Redis(**config.redis_connect)

  for server in config.servers:
    print('Updating stats for {server}'.format(server=server.url_slug))

    # Redis key name manager
    keys = Keys(config, server)

    # Limit our data to however much retention
    retention = Retention(r, keys, config)

    # Parse each of our soldat DIRs
    for soldat_dir in server.dirs:

      # Support getting logs via local files or ssh or ftp
      if server.log_source == 'local':
        filemanager = LocalFileManager(r, keys, soldat_dir)
      elif server.log_source == 'ssh':
        filemanager = SshFileManager(r, keys, soldat_dir, server.connection_options)
      elif server.log_source == 'ftp':
        filemanager = FtpFileManager(r, keys, soldat_dir, server.connection_options)

      # Console logs
      update_events(r, keys, retention, filemanager)

    # Trim old events
    retention.run_retention()
    print('Updating took {0} seconds'.format(round(time.time() - start, 2)))


@click.command()
@click.option(
    '--config_path',
    '-c',
    help='Path to config yaml file.',
    default=lambda: os.getenv('PYSTATS_CONF'),
    type=click.Path(exists=True, dir_okay=False),
    required=True)
def run_site(config_path):
  '''
    Spawn flask app. Pass me path to config file with redis connection + key
    prefix settings.
  '''

  config = Config(config_path)
  app = init_app(config_path)
  app.run(**config.flask_run)
