from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterable, Iterable, Optional, Dict, Any, List, Union

from mockfirestore.async_document import AsyncDocumentReference
from mockfirestore.async_collection import AsyncCollectionReference
from mockfirestore.async_transaction import AsyncTransaction
from mockfirestore.client import MockFirestore
from mockfirestore.document import DocumentSnapshot


class FirestoreBatchType(Enum):
    SET = "SET"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class FirestoreBatchOps:
    type: FirestoreBatchType
    doc_ref: AsyncDocumentReference
    data: Optional[Dict[str, Any]] = None
    kwargs: Optional[Dict[str, Any]] = None


class AsyncMockFirestore(MockFirestore):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._async_store_ref = self

    def document(self, path: str) -> AsyncDocumentReference:
        doc = super().document(path)
        assert isinstance(doc, AsyncDocumentReference)
        return doc

    def collection(self, path: str) -> AsyncCollectionReference:
        path = path.split("/")

        if len(path) % 2 != 1:
            raise Exception("Cannot create collection at path {}".format(path))

        name = path[-1]
        if len(path) > 1:
            current_position = self._ensure_path(path)
            return current_position.collection(name)
        else:
            if name not in self._data:
                self._data[name] = {}
            return AsyncCollectionReference(self._data, [name])

    async def collections(self) -> AsyncIterable[AsyncCollectionReference]:
        for collection_name in self._data:
            yield AsyncCollectionReference(self._data, [collection_name])

    async def get_all(
            self,
            references: Iterable[AsyncDocumentReference],
            field_paths=None,
            transaction=None,
    ) -> AsyncIterable[DocumentSnapshot]:
        for doc_ref in set(references):
            yield await doc_ref.get()

    def transaction(self, **kwargs) -> AsyncTransaction:
        return AsyncTransaction(self, **kwargs)

    def batch(self):
        new_batch_store_ref = BatchAsyncInternal()
        new_batch_store_ref._data = self._async_store_ref._data
        del self._async_store_ref
        self._async_store_ref = new_batch_store_ref
        return self._async_store_ref


class BatchAsyncInternal(AsyncMockFirestore):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._args = args
        self._kwargs = kwargs
        self._ops_queue: List[FirestoreBatchOps] = []

    def __len__(self):
        return len(self._ops_queue)

    def batch(self):
        new_batch = BatchAsyncInternal(*self._args, **self._kwargs)
        new_batch._data = self._data
        return new_batch

    async def commit(self) -> List[Any]:
        results = []
        for op in self._ops_queue:
            if op.type == FirestoreBatchType.SET:
                results.append(await op.doc_ref.set(op.data, {"merge": op.kwargs["merge"]}))
            elif op.type == FirestoreBatchType.UPDATE:
                results.append(await op.doc_ref.update(op.data))
            elif op.type == FirestoreBatchType.DELETE:
                results.append(await op.doc_ref.delete())
            else:
                raise NotImplementedError
        return results

    def set( # noqa
        self,
        reference: AsyncDocumentReference,
        document_data: dict,
        merge: Union[bool, list] = False,
    ) -> None:
        self._ops_queue.append(
            FirestoreBatchOps(FirestoreBatchType.SET, reference, document_data, {"merge": merge})
        )

    def update(
        self,
        reference: AsyncDocumentReference,
        field_updates: dict,
        option=None
    ) -> None:
        self._ops_queue.append(
            FirestoreBatchOps(FirestoreBatchType.UPDATE, reference, field_updates)
        )

    def delete(
        self, reference: AsyncDocumentReference, option=None
    ) -> None:
        self._ops_queue.append(
            FirestoreBatchOps(FirestoreBatchType.DELETE, reference, None, None)
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.commit()
