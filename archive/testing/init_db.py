from aproject.db import init_schema

if __name__ == "__main__":
    print("Veritabanı şeması oluşturuluyor...")
    init_schema()
    print("Tamamlandı.")
