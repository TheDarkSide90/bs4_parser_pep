import re
import logging
from urllib.parse import urljoin
from collections import Counter

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from constants import (
    BASE_DIR, EXPECTED_STATUS, MAIN_DOC_URL, PEP_DOC_URL
)
from configs import configure_argument_parser, configure_logging
from exceptions import UlTagNotFound
from outputs import control_output
from utils import get_response, find_tag

logger = logging.getLogger(__name__)


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all('li', attrs={
        'class': 'toctree-l1'
        })

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        version_link = urljoin(whats_new_url, version_a_tag['href'])
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append(
            (version_link, h1.text, dl_text)
        )

    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise UlTagNotFound('Ничего не нашлось')
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (link, version, status)
        )
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_tag = find_tag(soup, 'div', {'role': 'main'})
    table_tag = find_tag(main_tag, 'table', {'class': 'docutils'})
    pdf_a4_tag = find_tag(table_tag, 'a', {
        'href': re.compile(r'.+html\.zip$')
        })
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = get_response(session, archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logger.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    response = get_response(session, PEP_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    statuses = Counter()
    mismatches = []
    section = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    a_href = find_tag(section, 'a', attrs={'class': 'reference internal'})
    link = a_href['href']
    pep_list_link = urljoin(PEP_DOC_URL, link)
    response = get_response(session, pep_list_link)
    link_soup = BeautifulSoup(response.text, features='lxml')
    section = find_tag(link_soup, 'section', attrs={'id': 'numerical-index'})
    table = find_tag(section, 'table', attrs={'class': 'pep-zero-table'})
    tbody = find_tag(table, 'tbody')
    rows = tbody.find_all('tr')
    for row in tqdm(rows[1:]):
        pep = row.find_all('td')
        pep_status = pep[0]
        preview_status = pep_status.text[1:]
        link = find_tag(row, 'a')
        pep_url = urljoin(PEP_DOC_URL, link['href'])
        response = get_response(session, pep_url)
        if response is None:
            logger.warning('Не получилось получить данные с сервера')
            continue
        pep_soup = BeautifulSoup(response.text, 'lxml')
        section = find_tag(pep_soup, 'section', attrs={'id': 'pep-content'})
        dl = find_tag(section, 'dl')
        status = dl.find(string='Status')
        status_value = status.parent.find_next_sibling('dd').text.strip()
        if preview_status not in EXPECTED_STATUS:
            logger.warning(
                'Неизвестный статус в общей таблице: %s. PEP: %s',
                preview_status,
                pep_url
            )
            continue
        if status_value not in EXPECTED_STATUS[preview_status]:
            mismatches.append(
                (
                    pep_url,
                    status_value,
                    EXPECTED_STATUS[preview_status],
                )
            )
        statuses[status_value] += 1
    if mismatches:
        message = ['Несовпадающие статусы:']

        for pep_url, status, expected_statuses in mismatches:
            message.extend([
                '',
                pep_url,
                '',
                f'Статус в карточке: {status}',
                '',
                f'Ожидаемые статусы: {expected_statuses}',
            ])

        logger.warning('\n'.join(message))
    results = [
        ('Статус', 'Количество'),
    ]

    results.extend(statuses.items())

    results.append(
        ('Total', sum(statuses.values()))
    )

    return results


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logger.info('Парсер запущен!')

    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logger.info(f'Аргументы командной строки: {args}')

    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()

    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)

    if results is not None:
        control_output(results, args)
    logger.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
