import csv
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
    parser.add_argument('--image-filter', type=bool, default=True)
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
        return item.main_img_url is not None

    # Center Monthly listed in a column
    filters = [price_filter]
    if args.image_filter:
        filters.append(img_filter)
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

    new_res.sort(key=lambda x:x.created_at)
    with open(f'items{args.at}.csv', 'w') as wfile:
        writer = csv.writer(wfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(Item.keys)
        for item in new_res:
            dct = item.get_dct()
            writer.writerow([dct[key] for key in Item.keys])

    res.sort(key=lambda x:x.created_at)
    print(*res[-args.number_of_results:], sep='\n')


if __name__ == '__main__':
    main(parse_args())
