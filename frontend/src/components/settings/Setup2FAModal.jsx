/**
 * Setup 2FA Modal Component
 * For: Marco @ Syneto/Orizon
 * Google Authenticator / Authy compatible TOTP
 */

import { useState, useEffect } from 'react'
import { FiX, FiCheck, FiCopy, FiAlertCircle } from 'react-icons/fi'
import { toast } from 'react-toastify'
import api from '../../services/apiService'

export default function Setup2FAModal({ onClose }) {
  const [step, setStep] = useState(1) // 1: QR Code, 2: Verify, 3: Backup Codes
  const [qrCode, setQrCode] = useState('')
  const [secret, setSecret] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [backupCodes, setBackupCodes] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    generateQRCode()
  }, [])

  const generateQRCode = async () => {
    try {
      setLoading(true)
      const data = await api.generate2FAQRCode()
      setQrCode(data.qr_code)
      setSecret(data.secret)
    } catch (error) {
      toast.error('Failed to generate 2FA setup')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const data = await api.enable2FA(verificationCode)
      setBackupCodes(data.backup_codes)
      setStep(3)
      toast.success('2FA enabled successfully!')
    } catch (error) {
      toast.error('Invalid verification code. Please try again.')
      setVerificationCode('')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard')
  }

  const handleComplete = () => {
    toast.success('2FA setup complete! Please log in again.')
    window.location.reload()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-700">
          <h2 className="text-2xl font-bold text-white">
            Setup Two-Factor Authentication
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition"
          >
            <FiX className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Step indicators */}
          <div className="flex justify-between mb-8">
            <StepIndicator number={1} label="Scan QR Code" active={step === 1} completed={step > 1} />
            <div className="flex-1 h-0.5 bg-gray-700 self-center mx-2 mt-4">
              <div className={`h-full bg-blue-500 transition-all ${step > 1 ? 'w-full' : 'w-0'}`}></div>
            </div>
            <StepIndicator number={2} label="Verify Code" active={step === 2} completed={step > 2} />
            <div className="flex-1 h-0.5 bg-gray-700 self-center mx-2 mt-4">
              <div className={`h-full bg-blue-500 transition-all ${step > 2 ? 'w-full' : 'w-0'}`}></div>
            </div>
            <StepIndicator number={3} label="Backup Codes" active={step === 3} completed={false} />
          </div>

          {/* Step 1: QR Code */}
          {step === 1 && (
            <div className="space-y-6">
              <div className="bg-blue-900 bg-opacity-30 border border-blue-500 rounded-lg p-4 flex gap-3">
                <FiAlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-200">
                  Install an authenticator app like <strong>Google Authenticator</strong> or{' '}
                  <strong>Authy</strong> on your mobile device before proceeding.
                </div>
              </div>

              {loading ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                </div>
              ) : (
                <>
                  {/* QR Code */}
                  <div className="flex flex-col items-center">
                    <p className="text-gray-300 mb-4">
                      Scan this QR code with your authenticator app:
                    </p>
                    {qrCode && (
                      <img
                        src={qrCode}
                        alt="2FA QR Code"
                        className="bg-white p-4 rounded-lg"
                      />
                    )}
                  </div>

                  {/* Manual entry */}
                  <div className="bg-gray-900 rounded-lg p-4">
                    <p className="text-gray-400 text-sm mb-2">
                      Or enter this code manually in your app:
                    </p>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 bg-gray-800 px-4 py-3 rounded text-white font-mono text-lg tracking-wider">
                        {secret}
                      </code>
                      <button
                        onClick={() => copyToClipboard(secret)}
                        className="p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
                        title="Copy to clipboard"
                      >
                        <FiCopy className="w-5 h-5" />
                      </button>
                    </div>
                  </div>

                  <button
                    onClick={() => setStep(2)}
                    className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
                  >
                    Continue to Verification
                  </button>
                </>
              )}
            </div>
          )}

          {/* Step 2: Verification */}
          {step === 2 && (
            <form onSubmit={handleVerify} className="space-y-6">
              <div className="text-center">
                <p className="text-gray-300 mb-6">
                  Enter the 6-digit code from your authenticator app to verify:
                </p>
                <input
                  type="text"
                  maxLength="6"
                  pattern="[0-9]{6}"
                  required
                  autoFocus
                  placeholder="000000"
                  className="w-48 px-6 py-4 bg-gray-700 border-2 border-gray-600 rounded-lg text-white text-center text-2xl font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 mx-auto block"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ''))}
                />
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="flex-1 px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={loading || verificationCode.length !== 6}
                  className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Verifying...' : 'Verify & Enable'}
                </button>
              </div>
            </form>
          )}

          {/* Step 3: Backup Codes */}
          {step === 3 && (
            <div className="space-y-6">
              <div className="bg-yellow-900 bg-opacity-30 border border-yellow-500 rounded-lg p-4 flex gap-3">
                <FiAlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-200">
                  <strong>Important:</strong> Save these backup codes in a secure location.
                  Each code can be used once if you lose access to your authenticator app.
                </div>
              </div>

              <div className="bg-gray-900 rounded-lg p-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-white font-semibold">Your Backup Codes</h3>
                  <button
                    onClick={() => copyToClipboard(backupCodes.join('\n'))}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2 transition text-sm"
                  >
                    <FiCopy className="w-4 h-4" />
                    Copy All
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {backupCodes.map((code, index) => (
                    <div
                      key={index}
                      className="bg-gray-800 px-4 py-3 rounded font-mono text-white text-center"
                    >
                      {code}
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={handleComplete}
                className="w-full px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition flex items-center justify-center gap-2"
              >
                <FiCheck className="w-5 h-5" />
                Complete Setup
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function StepIndicator({ number, label, active, completed }) {
  return (
    <div className="flex flex-col items-center">
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition ${
          completed
            ? 'bg-green-600 text-white'
            : active
            ? 'bg-blue-600 text-white'
            : 'bg-gray-700 text-gray-400'
        }`}
      >
        {completed ? <FiCheck /> : number}
      </div>
      <span className={`text-sm mt-2 ${active || completed ? 'text-white' : 'text-gray-500'}`}>
        {label}
      </span>
    </div>
  )
}
