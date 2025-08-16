"use client";

import { motion } from "framer-motion";
import {
  Shield,
  Zap,
  TrendingUp,
  Smartphone,
  Globe,
  Lock,
  BarChart3,
  Wallet,
} from "lucide-react";

const features = [
  {
    icon: Shield,
    title: "Enterprise Security",
    description:
      "Bank-grade security with multi-layer encryption, cold storage, and regular security audits.",
    color: "from-success-500 to-success-600",
  },
  {
    icon: Zap,
    title: "Lightning Fast",
    description:
      "Execute trades in milliseconds with our high-performance trading engine and global infrastructure.",
    color: "from-accent-500 to-accent-600",
  },
  {
    icon: TrendingUp,
    title: "Real-time Analytics",
    description:
      "Advanced charts, technical indicators, and portfolio analytics to make informed decisions.",
    color: "from-primary-500 to-primary-600",
  },
  {
    icon: Smartphone,
    title: "Mobile Money Integration",
    description:
      "Seamlessly deposit and withdraw using popular mobile money services worldwide.",
    color: "from-warning-500 to-warning-600",
  },
  {
    icon: Globe,
    title: "Global Access",
    description:
      "Trade from anywhere in the world with support for multiple languages and currencies.",
    color: "from-info-500 to-info-600",
  },
  {
    icon: Lock,
    title: "Regulated & Compliant",
    description:
      "Fully compliant with international regulations and licensed in multiple jurisdictions.",
    color: "from-purple-500 to-purple-600",
  },
  {
    icon: BarChart3,
    title: "Advanced Trading",
    description:
      "Spot trading, futures, options, and margin trading with advanced order types.",
    color: "from-indigo-500 to-indigo-600",
  },
  {
    icon: Wallet,
    title: "Multi-Asset Support",
    description:
      "Trade hundreds of cryptocurrencies, stocks, commodities, and forex pairs.",
    color: "from-pink-500 to-pink-600",
  },
];

export function FeaturesSection() {
  return (
    <section className="py-20 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Why Choose DWT Exchange?
          </h2>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            We combine cutting-edge technology with user-friendly design to
            deliver the best trading experience in the cryptocurrency market.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              viewport={{ once: true }}
              whileHover={{ y: -5 }}
              className="group"
            >
              <div className="card h-full hover:shadow-medium transition-all duration-300">
                <div
                  className={`w-12 h-12 bg-gradient-to-r ${feature.color} rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}
                >
                  <feature.icon className="w-6 h-6 text-white" />
                </div>

                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>

                <p className="text-gray-600 text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* CTA Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <div className="bg-gradient-to-r from-primary-600 to-accent-600 rounded-2xl p-8 text-white">
            <h3 className="text-2xl font-bold mb-4">Ready to Start Trading?</h3>
            <p className="text-lg mb-6 opacity-90">
              Join thousands of traders and start your cryptocurrency journey
              today.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button className="bg-white text-primary-600 hover:bg-gray-100 font-semibold py-3 px-6 rounded-lg transition-colors duration-200">
                Create Account
              </button>
              <button className="border-2 border-white text-white hover:bg-white hover:text-primary-600 font-semibold py-3 px-6 rounded-lg transition-colors duration-200">
                Learn More
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
