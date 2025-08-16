"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Eye,
  EyeOff,
  Mail,
  Lock,
  User,
  Phone,
  AlertCircle,
  Globe,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "react-hot-toast";
import { useAuth } from "@/components/auth/auth-provider";
import { AuthMiddleware } from "@/components/auth/auth-middleware";
import Header from "@/components/layout/header";
import Footer from "@/components/layout/footer";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { useEffect } from "react";

// Zod validation schema for signup form
const signupSchema = z
  .object({
    first_name: z.string().min(1, "First name is required").trim(),
    last_name: z.string().min(1, "Last name is required").trim(),
    email: z.string().email("Please enter a valid email address").trim(),
    phone_number: z.string().min(1, "Phone number is required").trim(),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters long")
      .regex(
        /(?=.*[a-z])/,
        "Password must contain at least one lowercase letter"
      )
      .regex(
        /(?=.*[A-Z])/,
        "Password must contain at least one uppercase letter"
      )
      .regex(/(?=.*\d)/, "Password must contain at least one number"),
    password_confirm: z.string().min(1, "Please confirm your password"),
    country: z.string().min(1, "Country is required"),
    sponsor_code: z.string().optional(),
    agreedToTerms: z.boolean().refine((val) => val === true, {
      message: "You must agree to the terms and conditions",
    }),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: "Passwords do not match",
    path: ["password_confirm"],
  });

type SignupFormData = z.infer<typeof signupSchema>;

const countries = [
  { code: "UG", name: "Uganda" },
  { code: "KE", name: "Kenya" },
  { code: "TZ", name: "Tanzania" },
  { code: "RW", name: "Rwanda" },
  { code: "NG", name: "Nigeria" },
  { code: "GH", name: "Ghana" },
  { code: "ZA", name: "South Africa" },
  { code: "US", name: "United States" },
  { code: "GB", name: "United Kingdom" },
  { code: "CA", name: "Canada" },
];

function SignUpContent() {
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string>("");

  const router = useRouter();
  const { register } = useAuth();

  const form = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      phone_number: "",
      password: "",
      password_confirm: "",
      country: "UG",
      sponsor_code: "",
      agreedToTerms: false,
    },
    mode: "onChange", // Enable real-time validation
  });

  // Monitor form state changes to debug clearing issues
  useEffect(() => {
    const subscription = form.watch((value, { name, type }) => {
      console.log("Form field changed:", { name, type, value });
    });
    return () => subscription.unsubscribe();
  }, [form]);

  // Monitor form values for debugging
  useEffect(() => {
    console.log("Form values changed:", form.getValues());
  }, [form.formState]);

  const onSubmit = async (data: SignupFormData) => {
    console.log("Form submission started with data:", data);
    console.log("Current form values before submission:", form.getValues());
    // setIsLoading(true);
    setSuccessMessage("");

    try {
      const success = await register({
        email: data.email,
        phone_number: data.phone_number,
        first_name: data.first_name,
        last_name: data.last_name,
        password: data.password,
        password_confirm: data.password_confirm,
        sponsor_code: data.sponsor_code || undefined,
        country: data.country,
      });

      console.log("Register method returned:", success);
      console.log("Form values after register call:", form.getValues());

      if (success) {
        console.log("Registration successful");
        setSuccessMessage(
          "Account created successfully! Please check your email for verification."
        );
        toast.success(
          "Account created successfully! Please check your email for verification."
        );

        // Don't reset form - let user see their data was submitted
        // form.reset();

        // Redirect after a longer delay to show the success message
        setTimeout(() => {
          router.push("/auth/verify-email");
        }, 3000);
      } else {
        console.log("Registration returned false");
        toast.error("Registration failed. Please try again.");

        // IMPORTANT: Preserve form data when registration returns false
        // Only clear passwords for security, keep all other fields
        form.setValue("password", "");
        form.setValue("password_confirm", "");

        // Ensure other fields retain their values
        form.setValue("first_name", data.first_name);
        form.setValue("last_name", data.last_name);
        form.setValue("email", data.email);
        form.setValue("phone_number", data.phone_number);
        form.setValue("country", data.country);
        form.setValue("sponsor_code", data.sponsor_code);
        form.setValue("agreedToTerms", data.agreedToTerms);

        console.log("Form data preserved after false return:", {
          first_name: data.first_name,
          last_name: data.last_name,
          email: data.email,
          phone_number: data.phone_number,
          country: data.country,
          sponsor_code: data.sponsor_code,
          agreedToTerms: data.agreedToTerms,
        });
        console.log("Form values after preservation:", form.getValues());
      }
    } catch (error: any) {
      console.error("Registration error:", error);

      // Handle validation errors from backend
      if (error.message) {
        try {
          const backendErrors = JSON.parse(error.message);

          // Map backend errors to form fields
          Object.entries(backendErrors).forEach(([key, value]) => {
            if (typeof value === "string" && key in data) {
              form.setError(key as keyof SignupFormData, {
                type: "server",
                message: value,
              });
            }
          });

          // Show first error as toast
          const firstError = Object.values(backendErrors)[0];
          if (typeof firstError === "string") {
            toast.error(firstError);
          }
        } catch {
          // If not JSON, show as general error
          toast.error(
            error.message || "Registration failed. Please try again."
          );
        }
      } else {
        toast.error("Registration failed. Please try again.");
      }

      // IMPORTANT: Preserve all form data except passwords for security
      // Only clear passwords, keep all other fields
      form.setValue("password", "");
      form.setValue("password_confirm", "");

      // Ensure other fields retain their values by explicitly setting them
      form.setValue("first_name", data.first_name);
      form.setValue("last_name", data.last_name);
      form.setValue("email", data.email);
      form.setValue("phone_number", data.phone_number);
      form.setValue("country", data.country);
      form.setValue("sponsor_code", data.sponsor_code);
      form.setValue("agreedToTerms", data.agreedToTerms);

      console.log("Form data preserved after error:", {
        first_name: data.first_name,
        last_name: data.last_name,
        email: data.email,
        phone_number: data.phone_number,
        country: data.country,
        sponsor_code: data.sponsor_code,
        agreedToTerms: data.agreedToTerms,
      });
      console.log("Form values after error preservation:", form.getValues());
    } finally {
      console.log("Captured finally");
      console.log("Final form values:", form.getValues());
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 transition-colors">
      <Header />

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-gray-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-md w-full space-y-8"
        >
          <div className="text-center">
            <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
              <User className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2 font-paypal">
              Create Your Account
            </h1>
            <p className="text-gray-600 dark:text-gray-300 text-lg font-paypal-light">
              Join thousands of users and start your crypto journey today
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 p-8 relative">
            {/* Success Message */}
            {successMessage && (
              <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg
                      className="h-5 w-5 text-green-400"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-green-800 dark:text-green-200">
                      {successMessage}
                    </p>
                  </div>
                </div>
              </div>
            )}

            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-6"
              >
                {/* Loading Overlay */}
                {isLoading && (
                  <div className="absolute inset-0 bg-white/80 dark:bg-gray-800/80 rounded-xl flex items-center justify-center z-10">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
                      <p className="text-gray-600 dark:text-gray-400">
                        Creating your account...
                      </p>
                    </div>
                  </div>
                )}

                {/* First Name and Last Name */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="first_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-semibold text-gray-900 dark:text-white">
                          First Name
                        </FormLabel>
                        <div className="relative">
                          <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500 dark:text-gray-400 z-10" />
                          <FormControl>
                            <Input
                              {...field}
                              type="text"
                              autoComplete="given-name"
                              placeholder="First name"
                              className="pl-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 border-gray-300 dark:border-gray-600 focus:ring-primary-500 focus:border-primary-500"
                            />
                          </FormControl>
                        </div>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="last_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-semibold text-gray-900 dark:text-white">
                          Last Name
                        </FormLabel>
                        <div className="relative">
                          <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500 dark:text-gray-400 z-10" />
                          <FormControl>
                            <Input
                              {...field}
                              type="text"
                              autoComplete="family-name"
                              placeholder="Last name"
                              className="pl-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 border-gray-300 dark:border-gray-600 focus:ring-primary-500 focus:border-primary-500"
                            />
                          </FormControl>
                        </div>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                {/* Email */}
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-semibold text-gray-900 dark:text-white">
                        Email Address
                      </FormLabel>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500 dark:text-gray-400 z-10" />
                        <FormControl>
                          <Input
                            {...field}
                            type="email"
                            autoComplete="email"
                            placeholder="Enter your email"
                            className="pl-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 border-gray-300 dark:border-gray-600 focus:ring-primary-500 focus:border-primary-500"
                          />
                        </FormControl>
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Phone Number */}
                <FormField
                  control={form.control}
                  name="phone_number"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-semibold text-gray-900 dark:text-white">
                        Phone Number
                      </FormLabel>
                      <div className="relative">
                        <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500 dark:text-gray-400 z-10" />
                        <FormControl>
                          <Input
                            {...field}
                            type="tel"
                            autoComplete="tel"
                            placeholder="Enter phone number"
                            className="pl-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 border-gray-300 dark:border-gray-600 focus:ring-primary-500 focus:border-primary-500"
                          />
                        </FormControl>
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Country */}
                <FormField
                  control={form.control}
                  name="country"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-semibold text-gray-900 dark:text-white">
                        Country
                      </FormLabel>
                      <div className="relative">
                        <Globe className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500 dark:text-gray-400 z-10" />
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                        >
                          <FormControl>
                            <SelectTrigger className="pl-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600 focus:ring-primary-500 focus:border-primary-500">
                              <SelectValue placeholder="Select a country" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {countries.map((country) => (
                              <SelectItem
                                key={country.code}
                                value={country.code}
                              >
                                {country.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Password */}
                <FormField
                  control={form.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-semibold text-gray-900 dark:text-white">
                        Password
                      </FormLabel>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500 dark:text-gray-400 z-10" />
                        <FormControl>
                          <Input
                            {...field}
                            type={showPassword ? "text" : "password"}
                            autoComplete="new-password"
                            placeholder="Create a strong password"
                            className="pl-10 pr-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 border-gray-300 dark:border-gray-600 focus:ring-primary-500 focus:border-primary-500"
                          />
                        </FormControl>
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                        >
                          {showPassword ? (
                            <EyeOff className="w-5 h-5" />
                          ) : (
                            <Eye className="w-5 h-5" />
                          )}
                        </button>
                      </div>
                      <FormMessage />
                      <p className="text-gray-700 dark:text-gray-300 text-sm mt-1">
                        Must be at least 8 characters with uppercase, lowercase,
                        and number
                      </p>
                    </FormItem>
                  )}
                />

                {/* Password Confirmation */}
                <FormField
                  control={form.control}
                  name="password_confirm"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-semibold text-gray-900 dark:text-white">
                        Confirm Password
                      </FormLabel>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500 dark:text-gray-400 z-10" />
                        <FormControl>
                          <Input
                            {...field}
                            type={showPasswordConfirm ? "text" : "password"}
                            autoComplete="new-password"
                            placeholder="Confirm your password"
                            className="pl-10 pr-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 border-gray-300 dark:border-gray-600 focus:ring-primary-500 focus:border-primary-500"
                          />
                        </FormControl>
                        <button
                          type="button"
                          onClick={() =>
                            setShowPasswordConfirm(!showPasswordConfirm)
                          }
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                        >
                          {showPasswordConfirm ? (
                            <EyeOff className="w-5 h-5" />
                          ) : (
                            <Eye className="w-5 h-5" />
                          )}
                        </button>
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Terms and Conditions */}
                <FormField
                  control={form.control}
                  name="agreedToTerms"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                      <FormControl>
                        <Checkbox
                          checked={field.value}
                          onCheckedChange={field.onChange}
                          className="mt-1"
                        />
                      </FormControl>
                      <div className="space-y-1 leading-none">
                        <FormLabel className="text-sm text-gray-700 dark:text-gray-300">
                          I agree to the{" "}
                          <Link
                            href="/terms"
                            target="_blank"
                            className="text-primary-600 dark:text-primary-400 hover:text-primary-500 dark:hover:text-primary-300 underline"
                          >
                            Terms and Conditions
                          </Link>{" "}
                          and{" "}
                          <Link
                            href="/privacy"
                            target="_blank"
                            className="text-primary-600 dark:text-primary-400 hover:text-primary-500 dark:hover:text-primary-300 underline"
                          >
                            Privacy Policy
                          </Link>
                        </FormLabel>
                        <FormMessage />
                      </div>
                    </FormItem>
                  )}
                />

                {/* Submit Button */}
                <Button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700 text-white py-3 px-4 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? "Creating Account..." : "Create Account"}
                </Button>

                {/* Sign In Link */}
                <div className="text-center">
                  <p className="text-gray-700 dark:text-gray-200">
                    Already have an account?{" "}
                    <Link
                      href="/auth/signin"
                      className="text-primary-600 dark:text-primary-400 hover:text-primary-500 dark:hover:text-primary-300 font-medium underline transition-colors"
                    >
                      Sign in here
                    </Link>
                  </p>
                </div>
              </form>
            </Form>
          </div>
        </motion.div>
      </div>

      <Footer />
    </div>
  );
}

export default function SignUpPage() {
  return (
    <AuthMiddleware requireAuth={false}>
      <SignUpContent />
    </AuthMiddleware>
  );
}
