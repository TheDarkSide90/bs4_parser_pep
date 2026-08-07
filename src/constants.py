from pathlib import Path

MAIN_DOC_URL = 'https://docs.python.org/3/'
PEP_DOC_URL = 'https://peps.python.org/'
BASE_DIR = Path(__file__).parent
DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}
PEP_ID = ['process-and-meta-peps',
          'other-informational-peps',
          'provisional-peps-provisionally-accepted-interface-may-still-change',
          'accepted-peps-accepted-may-not-be-implemented-yet',
          'open-peps-under-consideration',
          'finished-peps-done-with-a-stable-interface',
          'historical-meta-peps-and-informational-peps',
          'deferred-peps-postponed-pending-further-research-or-updates',
          'rejected-superseded-and-withdrawn-peps',
          'reserved-pep-numbers']
