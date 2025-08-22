"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  CheckCircle,
  XCircle,
  Mail,
  ArrowLeft,
  RefreshCw,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { toast } from "react-hot-toast";
import { AuthMiddleware } from "@/components/auth/auth-middleware";
import Header from "@/components/layout/header";
import Footer from "@/components/layout/footer";
import { apiClient } from "@/lib/api-client";

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [email, setEmail] = useState("");

  useEffect(() => {
    const loadUserEmail = async () => {
      // Get email from URL params or localStorage first
      const emailParam = searchParams.get("email");
      const storedEmail = localStorage.getItem("signup_email");
      
      if (emailParam || storedEmail) {
        setEmail(emailParam || storedEmail || "");
      } else {
        // If no email in params/storage, fetch from backend for authenticated users
        try {
          const response = await apiClient.getVerificationInfo();
          setEmail(response.email || "");
        } catch (error) {
          console.log("Could not fetch user email:", error);
          // User might not be authenticated, that's okay
        }
      }
    };

    loadUserEmail();
    setCountdown(30);
  }, [searchParams]);

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.length !== 6) {
      toast.error("Please enter all 6 digits");
      return;
    }

    setLoading(true);
    try {
      const data = await apiClient.verifyEmail(otp, email);
      toast.success("Email verified successfully!");
      localStorage.removeItem("signup_email");
      // User is already authenticated, redirect to dashboard
      router.push("/dashboard");
    } catch (error: any) {
      console.error("Verification error:", error);
      const message = error.response?.data?.message || "Invalid verification code";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    if (countdown > 0 || !email) return;

    setResendLoading(true);
    try {
      await apiClient.resendVerification(email);
      toast.success("Verification code sent successfully!");
      setCountdown(30);
    } catch (error: any) {
      console.error("Resend error:", error);
      const message = error.response?.data?.message || "Failed to resend code";
      toast.error(message);
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-colors">
      <Header />

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-md w-full space-y-8"
        >
          <div className="text-center">
            <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
              <Lock className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2 font-paypal">
              Verify Your Email
            </h1>
            <p className="text-gray-600 dark:text-gray-300 text-lg">
              We've sent a 6-digit verification code to
            </p>
            <p className="text-blue-600 dark:text-blue-400 font-semibold text-lg">
              {email}
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 p-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* OTP Input */}
              <div className="space-y-4">
                <div className="text-center text-gray-600 dark:text-gray-400 text-sm">
                  Enter the 6-digit code sent to{" "}
                  <span className="font-medium text-gray-900 dark:text-white">
                    {email}
                  </span>
                </div>
                <div className="flex justify-center">
                  <InputOTP
                    maxLength={6}
                    value={otp}
                    onChange={(value) => setOtp(value)}
                  >
                    <InputOTPGroup>
                      <InputOTPSlot index={0} />
                      <InputOTPSlot index={1} />
                      <InputOTPSlot index={2} />
                      <InputOTPSlot index={3} />
                      <InputOTPSlot index={4} />
                      <InputOTPSlot index={5} />
                    </InputOTPGroup>
                  </InputOTP>
                </div>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={loading || otp.length !== 6}
                className="w-full bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
              >
                {loading ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    <span>Verifying...</span>
                  </div>
                ) : (
                  "Verify Email"
                )}
              </Button>

              {/* Resend Code Section */}
              <div className="text-center space-y-4">
                <div className="text-gray-600 dark:text-gray-400 text-sm">
                  Didn't receive the code?
                </div>

                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleResendCode}
                  disabled={countdown > 0 || resendLoading}
                  className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 px-4 py-2 rounded-lg transition-all duration-200"
                >
                  {resendLoading ? (
                    <div className="flex items-center space-x-2">
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Sending...</span>
                    </div>
                  ) : countdown > 0 ? (
                    `Resend in ${countdown}s`
                  ) : (
                    <div className="flex items-center space-x-2">
                      <RefreshCw className="w-4 h-4" />
                      <span>Resend Code</span>
                    </div>
                  )}
                </Button>
              </div>

              {/* Back to Sign In */}
              <div className="text-center pt-4 border-t border-gray-200 dark:border-gray-700">
                <Link
                  href="/auth/signin"
                  className="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Sign In
                </Link>
              </div>
            </form>
          </div>

          {/* Help Text */}
          <div className="text-center text-sm text-gray-500 dark:text-gray-400">
            <p>Check your spam folder if you don't see the email</p>
            <p className="mt-1">
              Having trouble?{" "}
              <Link
                href="/support"
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                Contact Support
              </Link>
            </p>
          </div>
        </motion.div>
      </div>

      <Footer />
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <AuthMiddleware requireAuth={false}>
      <VerifyEmailContent />
    </AuthMiddleware>
  );
}
