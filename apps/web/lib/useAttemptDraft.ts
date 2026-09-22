'use client';
import {useEffect, useState} from 'react';
import {scopedKey} from './browserStorage';

export function useAttemptDraft(id: string) {
  const [attempt, setAttempt] = useState('');
  const [partial, setPartial] = useState(true);
  const [loadedId, setLoadedId] = useState<string | null>(null);
  const [storageError, setStorageError] = useState('');
  useEffect(() => {
    try {
      const value = localStorage.getItem(scopedKey('draft', id));
      if (value) {
        const draft = JSON.parse(value);
        setAttempt(typeof draft.attempt === 'string' ? draft.attempt : '');
        setPartial(draft.partial !== false);
      } else {
        setAttempt('');
        setPartial(true);
      }
    } catch {setStorageError('Draft recovery is unavailable in this browser. Save your attempt before leaving.');}
    setLoadedId(id);
  }, [id]);
  useEffect(() => {
    if (loadedId !== id) return;
    try {
      if (attempt) localStorage.setItem(scopedKey('draft', id), JSON.stringify({attempt, partial}));
      else localStorage.removeItem(scopedKey('draft', id));
    } catch {setStorageError('Your draft could not be stored on this device. Keep this page open until your attempt is saved.');}
  }, [attempt, partial, loadedId, id]);
  return {attempt, setAttempt, partial, setPartial, storageError};
}
