"use client";

import { motion } from "framer-motion";
import { Users, DollarSign, TrendingUp, Globe } from "lucide-react";
import { formatCurrency } from "@/lib/utils";

const stats = [
  {
    icon: Users,
    value: "50,000+",
    label: "Active Traders",
    change: "+12%",
    changeType: "positive" as const,
  },
  {
    icon: DollarSign,
    value: formatCurrency(2500000000, "USD"),
    label: "Total Trading Volume",
    change: "+8.5%",
    changeType: "positive" as const,
  },
  {
    icon: TrendingUp,
    value: "150+",
    label: "Supported Cryptocurrencies",
    change: "+5",
    changeType: "positive" as const,
  },
  {
    icon: Globe,
    value: "120+",
    label: "Countries Supported",
    change: "+3",
    changeType: "positive" as const,
  },
];

export function StatsSection() {
  return (
    <section className="py-20 bg-gradient-to-br from-primary-600 to-primary-800 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Trusted by Traders Worldwide
          </h2>
          <p className="text-xl opacity-90 max-w-2xl mx-auto">
            Our platform has grown to become one of the most trusted
            cryptocurrency exchanges, serving traders across the globe.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              viewport={{ once: true }}
              className="text-center group"
            >
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 hover:bg-white/20 transition-all duration-300">
                <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform duration-300">
                  <stat.icon className="w-8 h-8" />
                </div>

                <div className="text-3xl font-bold mb-2">{stat.value}</div>

                <div className="text-lg opacity-90 mb-2">{stat.label}</div>

                <div
                  className={`text-sm font-medium ${
                    stat.changeType === "positive"
                      ? "text-green-300"
                      : "text-red-300"
                  }`}
                >
                  {stat.change} from last month
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Additional info */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 max-w-4xl mx-auto">
            <h3 className="text-2xl font-bold mb-4">Industry Recognition</h3>
            <p className="text-lg opacity-90 mb-6">
              DWT Exchange has been recognized by leading financial institutions
              and regulatory bodies for our commitment to security, compliance,
              and innovation.
            </p>
            <div className="flex flex-wrap justify-center items-center gap-8 opacity-70">
              <div className="text-center">
                <div className="text-2xl font-bold">ISO 27001</div>
                <div className="text-sm">Information Security</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">SOC 2</div>
                <div className="text-sm">Type II Certified</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">PCI DSS</div>
                <div className="text-sm">Level 1 Compliant</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">GDPR</div>
                <div className="text-sm">Data Protection</div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
