import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Only run middleware on protected routes
  const protectedPaths = ['/dashboard', '/wallet', '/trading', '/admin']
  const isProtectedPath = protectedPaths.some(path => 
    request.nextUrl.pathname.startsWith(path)
  )

  // Skip middleware for auth pages and public routes
  if (!isProtectedPath || request.nextUrl.pathname.startsWith('/auth/')) {
    return NextResponse.next()
  }

  // Check if user has email-verification-required cookie (indicates unverified email)
  const verificationRequired = request.cookies.get('email-verification-required')
  
  if (verificationRequired && verificationRequired.value === 'true') {
    // Redirect to email verification page
    const url = request.nextUrl.clone()
    url.pathname = '/auth/verify-email'
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
