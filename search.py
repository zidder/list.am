import re
import requests
from html.parser import HTMLParser
from threading import Thread
from datetime import datetime


list_am_url = 'https://www.list.am'


class ItemParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'span' and ("itemprop", "datePosted") in attrs:
            self.dt = datetime.strptime(dict(attrs)['content'], '%Y-%m-%dT%H:%M:%S%z')


def _get_page(url, res, ind, *args, **kwargs):
    response = requests.get(url, *args, **kwargs)
    if response.status_code != 200 or response.url != url:
        return
    res[ind] = response.content


def get_npages(urls, *args, **kwargs):
    n = len(urls)
    res = [None for i in range(n)]
    threads = [Thread(target=_get_page, args=(url, res, ind) + args, kwargs=kwargs, daemon=True)
               for ind, url in enumerate(urls)]
    for t in threads: t.start()
    for t in threads: t.join()
    return res


class Item:
    price_regex = '([\$€[\d,]+|[\d,]+ ֏) (ամսական|օրական)'
    keys = [
        'url',
        'price',
        'rooms',
        'sqm',
        'agency',
        'created_at',
        'info',
    ]

    def __init__(self, url):
        self.price = None
        self.url = url
        self.info = None
        self.additional_info = None
        self.rooms = None
        self.sqm = None
        self.agency = False
        self.main_img_url = None
        self.created_at = None

    def set_price(self, price):
        m = re.match(self.price_regex, price)
        if not m:
            m = re.match('[\d,]+ ֏', price)
            if m:
                price = int(m.group(0)[:-1].strip().replace(',', ''))
                if 75000 < price < 300000:
                    self.price = price
                    return
                else:
                    price *= 365 / 12
                    if 75000 < price < 300000:
                        self.price = price
                        return
            return

        price_group = m.group(1)
        freq_group = m.group(2)
        if len(freq_group) == 6:
            # daily
            m = 365 / 12
        else:
            # monthly
            m = 1
        if price_group[0].isdigit():
            self.price = m * int(price_group[:-1].strip().replace(',', ''))
        else:
            if price_group[0] == '$':
                # USD rate ~ 430
                self.price = 430 * m * int(price_group[1:].strip().replace(',', ''))
            else:
                # EUR rate ~ 445
                self.price = 445 * m * int(price_group[1:].strip().replace(',', ''))

    def set_data(self, line):
        m = re.search('(\d) սեն', line)
        if m:
            self.rooms = int(m.group(1))

        # Note, dots here are any characters, not just dots (just in case)
        m = re.search('(\d+) ք.մ.', line)
        if m:
            self.sqm = int(m.group(1))
        self.info = line

    def update(self, content):
        # TODO: update updated_at and created_at times
        p = ItemParser()
        p.feed(content)
        self.created_at = getattr(p, 'dt')

    def __repr__(self):
        agency = '(Agency)' if self.agency else ''
        created_at = f' created at {self.created_at}' if hasattr(self, 'created_at') else ''
        return (f'<Item created at{created_at} {self.url} {agency}: '
                f'{self.price}AMD {self.rooms} rooms and {self.sqm} sqm>')

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return self.url == other.url

    def __ne__(self, other):
        return self.url != other.url

    def get_dct(self):
        return {
            'price': self.price,
            'url': self.url,
            'info': self.info,
            'rooms': self.rooms,
            'sqm': self.sqm,
            'agency': self.agency,
            'created_at': str(self.created_at)
        }


class ListAmParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.tree = []

    def handle_starttag(self, tag, attrs):
        href_in_attrs = None
        for attr in attrs:
            if attr[0] == 'href' and attr[1].startswith('/item'):
                href_in_attrs = attr[1]

        if tag == 'a' and href_in_attrs:
            assert self.tree == []
            self.tree.append((tag, dict(attrs)))
            self.items.append(Item('https://www.list.am' + href_in_attrs))
        elif self.tree:
            if tag != 'img':
                self.tree.append((tag, dict(attrs)))
            else:
                self.items[-1].main_img_url = dict(attrs).get('data-original')

    def handle_endtag(self, tag):
        if self.tree:
            self.tree.pop()
            if self.tree == []:
                # end item
                pass

    def handle_data(self, data):
        if not self.tree:
            return
        if len(self.tree) >= 3 and (self.tree[-3][0] == self.tree[-2][0] == self.tree[-1][0] == 'div'
                                    and self.tree[-1][1] == {'class': 'p'}):
            self.items[-1].set_price(data)
        elif self.tree[-1][0] == 'div' and self.tree[-1][1].get('class') == 'at':
            self.items[-1].set_data(data)
        elif self.tree[-1][0] == 'span' and data.strip() == 'Գործակալություն':
            self.items[-1].agency = True
        elif len(self.tree) >= 2 and (self.tree[-1][0] == self.tree[-2][0] == 'div'
                                      and self.tree[-1][1] == {}):
            self.items[-1].additional_info = data


def get_pages(url_template, *args, **kwargs):
    page = 1
    n = 20
    while True:
        urls = [url_template.format(page=pg) for pg in range(page, page + n)]
        pages = get_npages(urls, *args, **kwargs)
        pages = [i for i in pages if i is not None]
        if not pages:
            return
        yield from iter(pages)
        page += n


def chunks(items, n=20):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def parse(suburl, filters=None):
    url_template = list_am_url + suburl
    headers = {
        'Host': 'www.list.am',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:97.0) Gecko/20100101 Firefox/97.0'
    }
    res = set()
    for content in get_pages(url_template, headers=headers):
        parser = ListAmParser()
        parser.feed(content.decode())
        for item in parser.items:
            res.add(item)
    print(len(res))
    if filters:
        for f in filters:
            res = filter(f, res)
    res = list(res)
    print(len(res))
    for chunk in chunks(res):
        contents = get_npages([item.url for item in chunk], headers=headers)
        for item, content in zip(chunk, contents):
            item.update(content.decode())
    return res
