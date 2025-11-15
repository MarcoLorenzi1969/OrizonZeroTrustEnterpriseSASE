/**
 * Settings Page - User Settings and 2FA Management
 * For: Marco @ Syneto/Orizon
 */

import { useState } from 'react'
import { useSelector } from 'react-redux'
import { toast } from 'react-toastify'
import api from '../services/apiService'
import { FiUser, FiLock, FiShield, FiSave } from 'react-icons/fi'
import Setup2FAModal from '../components/settings/Setup2FAModal'

export default function SettingsPage() {
  const { user } = useSelector(state => state.auth)
  const [activeTab, setActiveTab] = useState('profile')
  const [show2FAModal, setShow2FAModal] = useState(false)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">Manage your account and security settings</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-700">
        <TabButton
          active={activeTab === 'profile'}
          onClick={() => setActiveTab('profile')}
          icon={<FiUser />}
        >
          Profile
        </TabButton>
        <TabButton
          active={activeTab === 'security'}
          onClick={() => setActiveTab('security')}
          icon={<FiShield />}
        >
          Security
        </TabButton>
        <TabButton
          active={activeTab === 'password'}
          onClick={() => setActiveTab('password')}
          icon={<FiLock />}
        >
          Password
        </TabButton>
      </div>

      {/* Content */}
      <div className="bg-gray-800 rounded-lg p-6">
        {activeTab === 'profile' && <ProfileSettings user={user} />}
        {activeTab === 'security' && (
          <SecuritySettings
            user={user}
            onSetup2FA={() => setShow2FAModal(true)}
          />
        )}
        {activeTab === 'password' && <PasswordSettings />}
      </div>

      {/* 2FA Setup Modal */}
      {show2FAModal && (
        <Setup2FAModal onClose={() => setShow2FAModal(false)} />
      )}
    </div>
  )
}

function TabButton({ active, onClick, icon, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 flex items-center gap-2 transition ${
        active
          ? 'text-blue-500 border-b-2 border-blue-500'
          : 'text-gray-400 hover:text-white'
      }`}
    >
      {icon}
      {children}
    </button>
  )
}

function ProfileSettings({ user }) {
  const [formData, setFormData] = useState({
    full_name: user?.full_name || '',
    email: user?.email || ''
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.updateUser(user.id, formData)
      toast.success('Profile updated successfully')
    } catch (error) {
      toast.error('Failed to update profile')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Full Name
        </label>
        <input
          type="text"
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white"
          value={formData.full_name}
          onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Email
        </label>
        <input
          type="email"
          disabled
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white opacity-60 cursor-not-allowed"
          value={formData.email}
        />
        <p className="text-xs text-gray-400 mt-1">Email cannot be changed</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Role
        </label>
        <input
          type="text"
          disabled
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white opacity-60 cursor-not-allowed capitalize"
          value={user?.role || 'N/A'}
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 disabled:opacity-50"
      >
        <FiSave />
        {loading ? 'Saving...' : 'Save Changes'}
      </button>
    </form>
  )
}

function SecuritySettings({ user, onSetup2FA }) {
  const has2FA = user?.totp_enabled

  const handleDisable2FA = async () => {
    const token = prompt('Enter your 2FA code to disable 2FA:')
    if (!token) return

    try {
      await api.disable2FA(token)
      toast.success('2FA disabled successfully')
      window.location.reload()
    } catch (error) {
      toast.error('Failed to disable 2FA - invalid code')
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-gray-700 rounded-lg p-6">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <FiShield className="text-blue-500" />
              Two-Factor Authentication (2FA)
            </h3>
            <p className="text-sm text-gray-400 mt-2">
              Add an extra layer of security to your account with TOTP 2FA.
              Compatible with Google Authenticator, Authy, and other apps.
            </p>
            <div className="mt-4">
              {has2FA ? (
                <div className="flex items-center gap-2">
                  <span className="text-green-500">✓ Enabled</span>
                  <span className="text-gray-400">|</span>
                  <span className="text-xs text-gray-500">
                    Enrolled on {new Date(user.totp_created_at).toLocaleDateString()}
                  </span>
                </div>
              ) : (
                <span className="text-yellow-500">⚠ Not Enabled</span>
              )}
            </div>
          </div>
          <div>
            {has2FA ? (
              <button
                onClick={handleDisable2FA}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
              >
                Disable 2FA
              </button>
            ) : (
              <button
                onClick={onSetup2FA}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
              >
                Enable 2FA
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="bg-gray-700 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Session Information</h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Last Login:</span>
            <span className="text-white">
              {user?.last_login
                ? new Date(user.last_login).toLocaleString()
                : 'N/A'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Account Created:</span>
            <span className="text-white">
              {user?.created_at
                ? new Date(user.created_at).toLocaleDateString()
                : 'N/A'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

function PasswordSettings() {
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (formData.newPassword !== formData.confirmPassword) {
      toast.error('Passwords do not match')
      return
    }

    if (formData.newPassword.length < 12) {
      toast.error('Password must be at least 12 characters')
      return
    }

    setLoading(true)
    try {
      await api.changePassword(formData.currentPassword, formData.newPassword)
      toast.success('Password changed successfully')
      setFormData({ currentPassword: '', newPassword: '', confirmPassword: '' })
    } catch (error) {
      toast.error('Failed to change password - check current password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Current Password
        </label>
        <input
          type="password"
          required
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white"
          value={formData.currentPassword}
          onChange={(e) => setFormData({ ...formData, currentPassword: e.target.value })}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          New Password
        </label>
        <input
          type="password"
          required
          minLength="12"
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white"
          value={formData.newPassword}
          onChange={(e) => setFormData({ ...formData, newPassword: e.target.value })}
        />
        <p className="text-xs text-gray-400 mt-1">
          Min 12 characters, must include uppercase, lowercase, number, and symbol
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Confirm New Password
        </label>
        <input
          type="password"
          required
          className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white"
          value={formData.confirmPassword}
          onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 disabled:opacity-50"
      >
        <FiLock />
        {loading ? 'Changing Password...' : 'Change Password'}
      </button>
    </form>
  )
}
