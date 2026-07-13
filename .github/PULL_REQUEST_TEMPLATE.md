# Pull Request: Fix syntax, indentation, and cache bugs

## Description
This PR fixes three critical bugs in the Search and Games routers:

### Bug Fixes

1. **Games Router - Indentation Bug (Line 101)**
   - **Issue**: `game_id` validation was not properly indented inside the `send_game_invitation` function
   - **Impact**: Caused syntax error preventing the endpoint from working
   - **Fix**: Properly indented the validation check inside the function body

2. **Search Router - Null Pointer Error (Line 69)**
   - **Issue**: `cached.cached_at` could be `None`, causing TypeError when subtracting from datetime
   - **Impact**: Cache validation would crash if cached_at was not set
   - **Fix**: Added null check: `if cached and cached.cached_at and ...`

3. **Search Router - Duplicate Object Creation (Lines 150-162)**
   - **Issue**: `Search` object was created twice, with the first creation being unused
   - **Impact**: Wasted resources and confusing code
   - **Fix**: Removed duplicate creation, keeping only the necessary one

## Type of Change
- [x] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)

## How to Test
1. Test the games invitation endpoint with valid and invalid game_ids
2. Verify search caching works without crashing
3. Confirm search records are created correctly in the database

## Files Changed
- `apps/lominii/games/router.py`
- `apps/lominii/search/router.py`

## Related Issues
- Fixes syntax error in games router
- Fixes potential null pointer exception in search cache
- Cleans up redundant code in search router
