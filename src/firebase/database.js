import { db } from './config';
import { 
  collection, 
  addDoc, 
  getDocs,
  doc,
  getDoc,
  updateDoc,
  deleteDoc
} from 'firebase/firestore';

export const createDoc = (collectionName, data) => {
  return addDoc(collection(db, collectionName), data);
};

export const getAllDocs = (collectionName) => {
  return getDocs(collection(db, collectionName));
};

export const getOneDoc = (collectionName, docId) => {
  return getDoc(doc(db, collectionName, docId));
};

export const updateOneDoc = (collectionName, docId, data) => {
  return updateDoc(doc(db, collectionName, docId), data);
};

export const deleteOneDoc = (collectionName, docId) => {
  return deleteDoc(doc(db, collectionName, docId));
};