import json
import pickle
import argparse
from search import parse, Item


at = {
    'Աջափնյակ': 2,
    'Արաբկիր': 3,
    'Ավան': 4,
    'Դավիթաշեն': 5,
    'Էրեբունի': 6,
    'Քանաքեռ Զեյթուն': 7,
    'Կենտրոն': 8,
    'Մալաթիա Սեբաստիա': 9,
    'Նոր Նորք': 10,
    'Շենգավիթ': 13,
    'Նորք Մարաշ': 11,
    'Նուբարաշեն': 12
}


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--low-price', type=int, default=100000)
    parser.add_argument('--high-price', type=int, default=300000)
    parser.add_argument('--ignore-cache', type=bool, default=False)
    parser.add_argument('--number-of-results', '-n', type=int, default=100,
                        help="0 for seeing all results, can be a lot")
    parser.add_argument('--at', type=int, default=8,
                        help='Use the following mapping\n'
                             + json.dumps(at, indent=2, ensure_ascii=False))
    return parser.parse_args()


def main(args):
    prev_res = []

    try:
        with open(f'items{args.at}.pkl', 'rb') as rfile:
            prev_res = pickle.load(rfile)
    except Exception:
        pass

    cache = {item.url for item in prev_res}

    def price_filter(item):
        return (
            item.price is not None
            and args.low_price <= item.price <= args.high_price
        )

    def cache_filter(item):
        return item.url not in cache

    def img_filter(item):
        # FIXME: IDK if I need this
        if item.main_img_url is None: return False
        a = ['657/43705657',
             '654/43705654',
             '656/43705656',
             '658/43705658',
             '652/43705652',
             '655/43705655',
             '647/43705647',
             '653/43705653',
             '648/43705648',
             '649/43705649',
             '651/43705651',
             '650/43705650']

        for img_url in a:
            if img_url in item.main_img_url:
                return True
        return False

    # Center Monthly listed in a column
    filters = [price_filter]
    if not args.ignore_cache:
        filters.append(cache_filter)
    res = list(set(
        parse('/category/56/{page}?pfreq=1&n=' + str(args.at) + '&gl=2', filters)
    ))
    if not args.ignore_cache:
        new_res = prev_res + res
    else:
        new_res = res

    with open(f'items{args.at}.pkl', 'wb') as wfile:
        pickle.dump(new_res, wfile)

    res.sort(key=lambda x:x.created_at)
    print(*res[-args.number_of_results:], sep='\n')


if __name__ == '__main__':
    main(parse_args())
