from pymongo import MongoClient
import json

def check_database():
    """Kiểm tra dữ liệu có sẵn trong MongoDB"""
    client = MongoClient('mongodb://root:123456@localhost:27017/')
    
    try:
        # Test connection
        client.admin.command('ping')
        print("✅ Kết nối MongoDB thành công!")
        
        # List all databases
        db_list = client.list_database_names()
        print(f"📊 Databases: {db_list}")
        
        # Check job_data database
        if 'job_data' in db_list:
            db = client['job_data']
            collections = db.list_collection_names()
            print(f"📂 Collections trong job_data: {collections}")
            
            # Check each collection
            for collection_name in collections:
                collection = db[collection_name]
                total_docs = collection.count_documents({})
                print(f"\n📄 Collection '{collection_name}': {total_docs} documents")
                
                if total_docs > 0:
                    # Sample data
                    sample_doc = collection.find_one()
                    if sample_doc:
                        print(f"  Sample keys: {list(sample_doc.keys())}")
                        if 'category' in sample_doc:
                            print(f"  Category: {sample_doc['category']}")
                        if 'title' in sample_doc:
                            print(f"  Sample title: {sample_doc['title'][:50]}...")
                            
        else:
            print("❌ Database 'job_data' không tồn tại")
            
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    check_database()