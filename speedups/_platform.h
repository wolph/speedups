/*
 * Platform abstraction for _stl.pyx
 *
 * Replaces deprecated Cython IF UNAME_SYSNAME conditionals with
 * C preprocessor macros.
 */
#ifndef SPEEDUPS_PLATFORM_H
#define SPEEDUPS_PLATFORM_H

#ifdef _WIN32
#include <io.h>
#else
#include <unistd.h>
#endif

/*
 * Locale handling: force C locale for consistent sscanf/fprintf float
 * parsing. Available on POSIX (Linux, macOS); no-op on Windows.
 */
#if !defined(_WIN32)
#include <locale.h>

typedef locale_t spd_locale_t;

static inline spd_locale_t spd_create_c_locale(void) {
    return newlocale(LC_NUMERIC_MASK, "C", (locale_t)0);
}

static inline spd_locale_t spd_uselocale(spd_locale_t loc) {
    return uselocale(loc);
}

static inline void spd_freelocale(spd_locale_t loc) {
    freelocale(loc);
}

#else  /* _WIN32 */

typedef int spd_locale_t;

static inline spd_locale_t spd_create_c_locale(void) { return 0; }
static inline spd_locale_t spd_uselocale(spd_locale_t loc) {
    (void)loc; return 0;
}
static inline void spd_freelocale(spd_locale_t loc) { (void)loc; }

#endif

#endif /* SPEEDUPS_PLATFORM_H */
