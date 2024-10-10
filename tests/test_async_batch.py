import aiounittest
from mockfirestore import AsyncMockFirestore


class TestAsyncMockFirestore(aiounittest.AsyncTestCase):
    async def test_batch_commit(self):
        fs = AsyncMockFirestore()
        data = [
            ("foo", {"value": "Foo"}),
            ("bar", {"value": "Bar"}),
            ("baz", {"value": "Baz"}),
        ]
        collection_path = "sample_collection"

        batch_store = fs.batch()
        coll_ref = fs.collection(collection_path)
        doc_ref_data = [(coll_ref.document(key), datum) for (key, datum) in data]

        # Batch write data
        for doc_ref, datum in doc_ref_data:
            batch_store.set(doc_ref, datum)
        await batch_store.commit()

        # Async sequential read
        for doc_ref, datum in doc_ref_data:
            result = await doc_ref.get()
            assert result.exists
            assert result.to_dict() == datum

    async def test_batch_commit_multiple(self):
        fs = AsyncMockFirestore()
        collection_path = "sample_collection"
        fs._data = {
            collection_path: {
                "sample": {"value": "Sample"}
            }
        }
        data_1 = [
            ("foo", {"value": "Foo"}),
            ("bar", {"value": "Bar"}),
            ("baz", {"value": "Baz"}),
            ("quux", {"value": "Quux"})
        ]
        data_2 = [
            ("foo", {"value": "Baz"}),
            ("baz", {"value": "Foo"}),
            ("qux", {"value": "Qux"})
        ]

        coll_ref = fs.collection(collection_path)
        doc_ref_data_1 = [(coll_ref.document(key), datum) for (key, datum) in data_1]
        doc_ref_data_2 = [(coll_ref.document(key), datum) for (key, datum) in data_2]

        batch_1 = fs.batch()
        for doc_ref, datum in doc_ref_data_1:
            batch_1.set(doc_ref, datum)
        batch_1.delete(coll_ref.document("sample"))
        await batch_1.commit()

        batch_2 = fs.batch()
        for doc_ref, datum in doc_ref_data_2:
            batch_2.set(doc_ref, datum)
        batch_2.delete(coll_ref.document("quux"))
        await batch_2.commit()

        assert fs._data == {
            collection_path: {
                "foo": {"value": "Baz"},
                "bar": {"value": "Bar"},
                "baz": {"value": "Foo"},
                "qux": {"value": "Qux"}
            }
        }
