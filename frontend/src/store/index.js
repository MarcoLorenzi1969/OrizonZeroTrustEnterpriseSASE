/**
 * Orizon Zero Trust Connect - Redux Store
 * For: Marco @ Syneto/Orizon
 */

import { configureStore } from '@reduxjs/toolkit'
import authReducer from './slices/authSlice'
import nodesReducer from './slices/nodesSlice'
import tunnelsReducer from './slices/tunnelsSlice'
import aclReducer from './slices/aclSlice'
import auditReducer from './slices/auditSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    nodes: nodesReducer,
    tunnels: tunnelsReducer,
    acl: aclReducer,
    audit: auditReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ['websocket/messageReceived'],
      },
    }),
})

export default store
