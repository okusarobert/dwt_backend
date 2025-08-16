"use client";

import { Suspense } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  ArrowRight,
  LogIn,
  Shield,
  Zap,
  Clock,
  DollarSign,
  Users,
  BarChart3,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { RealTimePrices } from "@/components/crypto/real-time-prices";
import Header from "@/components/layout/header";
import Footer from "@/components/layout/footer";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors">
      <Header />

      {/* Hero Section */}
      <section className="py-20 bg-gradient-to-br from-primary-50 via-white to-accent-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 text-sm font-medium">
                <TrendingUp className="w-4 h-4 mr-2" />
                #1 Trusted Crypto Exchange
              </div>
              <h1 className="text-5xl lg:text-6xl font-bold text-gray-900 dark:text-white leading-tight">
                Trade Crypto{" "}
                <span className="bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent">
                  Like a Pro
                </span>
              </h1>
              <p className="text-xl text-gray-600 dark:text-gray-300 leading-relaxed">
                Join millions of traders on the world's most secure and
                user-friendly cryptocurrency exchange. Start with as little as
                $10.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Button
                  size="lg"
                  asChild
                  className="bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700 text-lg px-8 py-4"
                >
                  <Link href="/auth/signup">
                    Start Trading Now
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  className="text-lg px-8 py-4 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                >
                  Learn More
                </Button>
              </div>
              <div className="flex items-center space-x-8 pt-4">
                <div className="flex items-center space-x-2">
                  <Shield className="w-5 h-5 text-green-600 dark:text-green-400" />
                  <span className="text-gray-600 dark:text-gray-400">
                    Bank-level Security
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <Zap className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
                  <span className="text-gray-600 dark:text-gray-400">
                    Lightning Fast
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  <span className="text-gray-600 dark:text-gray-400">
                    24/7 Trading
                  </span>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-4">
                <Card className="p-6 text-center bg-white dark:bg-gray-800 shadow-lg dark:shadow-gray-900/50 transition-colors">
                  <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">
                    10
                  </div>
                  <div className="text-gray-600 dark:text-gray-400">
                    Live Cryptocurrencies
                  </div>
                </Card>
                <Card className="p-6 text-center bg-white dark:bg-gray-800 shadow-lg dark:shadow-gray-900/50 transition-colors">
                  <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">
                    Real-time
                  </div>
                  <div className="text-gray-600 dark:text-gray-400">
                    Price Streaming
                  </div>
                </Card>
              </div>
              <div className="space-y-4 pt-8">
                <Card className="p-6 text-center bg-white dark:bg-gray-800 shadow-lg dark:shadow-gray-900/50 transition-colors">
                  <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">
                    <span className="text-2xl">∞</span>
                  </div>
                  <div className="text-gray-600 dark:text-gray-400">
                    Trading Pairs
                  </div>
                </Card>
                <Card className="p-6 text-center bg-white dark:bg-gray-800 shadow-lg dark:shadow-gray-900/50 transition-colors">
                  <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">
                    <span className="text-2xl">⚡</span>
                  </div>
                  <div className="text-gray-600 dark:text-gray-400">
                    Lightning Fast
                  </div>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Why Choose Section */}
      <section className="py-20 bg-gray-50 dark:bg-gray-800 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
              Why Choose DT Exchange?
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-200 max-w-3xl mx-auto">
              Experience the perfect combination of security, speed, and
              simplicity in cryptocurrency trading
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <Card className="p-8 text-center bg-white dark:bg-gray-800 shadow-lg hover:shadow-xl transition-shadow dark:shadow-gray-900/50">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Shield className="w-8 h-8 text-green-600 dark:text-green-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                Bank-Level Security
              </h3>
              <p className="text-gray-600 dark:text-gray-200">
                Your funds are protected by industry-leading security measures
                including cold storage and multi-signature wallets.
              </p>
            </Card>
            <Card className="p-8 text-center bg-white dark:bg-gray-800 shadow-lg hover:shadow-xl transition-shadow dark:shadow-gray-900/50">
              <div className="w-16 h-16 bg-orange-100 dark:bg-orange-900/30 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Zap className="w-8 h-8 text-orange-600 dark:text-orange-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                Lightning Fast Trading
              </h3>
              <p className="text-gray-600 dark:text-gray-200">
                Execute trades in milliseconds with our high-performance
                matching engine and advanced order types.
              </p>
            </Card>
            <Card className="p-8 text-center bg-white dark:bg-gray-800 shadow-lg hover:shadow-xl transition-shadow dark:shadow-gray-900/50">
              <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <DollarSign className="w-8 h-8 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                Lowest Fees
              </h3>
              <p className="text-gray-600 dark:text-gray-200">
                Trade with confidence knowing you're getting the best rates with
                fees as low as 0.1% per transaction.
              </p>
            </Card>
            <Card className="p-8 text-center bg-white dark:bg-gray-800 shadow-lg hover:shadow-xl transition-shadow dark:shadow-gray-900/50">
              <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/30 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Users className="w-8 h-8 text-purple-600 dark:text-purple-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                24/7 Support
              </h3>
              <p className="text-gray-600 dark:text-gray-200">
                Get help whenever you need it with our round-the-clock customer
                support team.
              </p>
            </Card>
            <Card className="p-8 text-center bg-white dark:bg-gray-800 shadow-lg hover:shadow-xl transition-shadow dark:shadow-gray-900/50">
              <div className="w-16 h-16 bg-purple-100 dark:bg-purple-900/30 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Shield className="w-8 h-8 text-purple-600 dark:text-purple-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                Regulatory Compliance
              </h3>
              <p className="text-gray-600 dark:text-gray-200">
                Trade with peace of mind on a platform that meets the highest
                regulatory standards.
              </p>
            </Card>
            <Card className="p-8 text-center bg-white dark:bg-gray-800 shadow-lg hover:shadow-xl transition-shadow dark:shadow-gray-900/50">
              <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <BarChart3 className="w-8 h-8 text-red-600 dark:text-red-400" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
                Advanced Analytics
              </h3>
              <p className="text-gray-600 dark:text-gray-200">
                Make informed decisions with professional-grade charts,
                technical indicators, and real-time data.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* Top Cryptocurrencies Section */}
      <section className="py-20 bg-white dark:bg-gray-900 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <RealTimePrices />
        </div>
      </section>

      {/* Trust Section */}
      <section className="py-20 bg-gray-50 dark:bg-gray-800 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
              Trusted by millions worldwide
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-200 max-w-3xl mx-auto">
              Join over 10 million users who trust our platform for secure and
              efficient crypto trading
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Card className="p-8 text-center bg-white dark:bg-gray-800 shadow-lg dark:shadow-gray-900/50">
              <div className="text-gray-600 dark:text-gray-200 mb-6 text-lg italic">
                "The most intuitive crypto exchange I've ever used. Security is
                top-notch."
              </div>
              <div className="font-bold text-gray-900 dark:text-white">
                Sarah Chen
              </div>
              <div className="text-gray-500 dark:text-gray-300">
                Professional Trader
              </div>
            </Card>
            <Card className="p-8 text-center bg-white dark:bg-gray-800 shadow-lg dark:shadow-gray-900/50">
              <div className="text-gray-600 dark:text-gray-200 mb-6 text-lg italic">
                "Low fees and lightning-fast transactions. Perfect for my
                trading strategy."
              </div>
              <div className="font-bold text-gray-900 dark:text-white">
                Michael Rodriguez
              </div>
              <div className="text-gray-500 dark:text-gray-300">
                Crypto Investor
              </div>
            </Card>
            <Card className="p-8 text-center bg-white dark:bg-gray-800 shadow-lg dark:shadow-gray-900/50">
              <div className="text-gray-600 dark:text-gray-200 mb-6 text-lg italic">
                "Excellent customer support and real-time crypto price
                streaming."
              </div>
              <div className="font-bold text-gray-900 dark:text-white">
                Emma Thompson
              </div>
              <div className="text-gray-500 dark:text-gray-300">
                DeFi Enthusiast
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-primary-600 to-accent-600 dark:from-primary-700 dark:to-accent-700 transition-colors">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl font-bold text-white mb-4">
            Ready to start trading?
          </h2>
          <p className="text-xl text-primary-100 dark:text-primary-200 mb-8">
            Start your crypto journey today with real-time price data. Sign up
            in minutes.
          </p>
          <Button
            size="lg"
            asChild
            className="bg-white text-primary-600 hover:bg-gray-100 dark:bg-white dark:text-primary-700 dark:hover:bg-gray-100 text-lg px-8 py-4"
          >
            <Link href="/auth/signup">Get Started Now</Link>
          </Button>
        </div>
      </section>

      <Footer />
    </div>
  );
}
