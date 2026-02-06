from datasets import load_dataset

def inspect(config_name: str):
    print("=" * 60)
    print("CONFIG =", config_name)

    ds = load_dataset("K-and-K/perturbed-knights-and-knaves", config_name)
    print("DS TYPE:", type(ds))
    print("AVAILABLE SPLITS:", list(ds.keys()))

    # 取第一个 split，不猜名字
    first_split = list(ds.keys())[0]
    data = ds[first_split]

    print("USING SPLIT:", first_split)
    print("dataset size:", len(data))

    ex = data[0]
    print("keys:", list(ex.keys()))
    print("raw example:")
    for k, v in ex.items():
        print(f"{k}: {v}")

def main():
    inspect("train")
    inspect("test")

if __name__ == "__main__":
    main()
