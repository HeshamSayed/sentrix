# 🎛️ Discount Configuration Guide

## Overview

The SENTRIX platform now has **configurable discount percentages** that can be managed directly from the Django admin panel. This allows the backoffice team to adjust or disable discounts without code changes.

---

## ✅ What Was Implemented

### 1. Discount Field in SubscriptionPlan Model
- **Field**: `annual_discount_percentage`
- **Type**: Decimal (5 digits, 2 decimal places)
- **Default**: 16.67% (equivalent to 2 months free)
- **Range**: 0% to 99.99%

### 2. Auto-Calculation
- Annual price is **automatically calculated** when discount is set
- Formula: `annual_price = (monthly_price × 12) × (1 - discount_percentage / 100)`
- Updates automatically when you save the plan

### 3. Django Admin Interface
- Beautiful admin panel with color-coded displays
- Shows savings amount and free months equivalent
- Easy to edit and update

---

## 📋 How to Use (Django Admin)

### Accessing Django Admin

1. **URL**: `http://localhost:8000/admin/` (or your domain)
2. **Create Superuser** (first time only):
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```
3. **Login** with your credentials

### Managing Subscription Plans

#### Navigate to Subscription Plans:
1. Go to **Django Admin**
2. Click on **Core** section
3. Click on **Subscription Plans**

#### Edit a Plan:
1. Click on the plan you want to edit (e.g., "Startup")
2. Scroll to **Pricing** section
3. Modify `Annual discount percentage` field
4. Click **Save**

---

## 💡 Common Discount Scenarios

### Scenario 1: 2 Months Free (Current Default)
```
Discount: 16.67%
Example (Startup Plan):
  - Monthly: $149
  - Annual without discount: $149 × 12 = $1,788
  - Annual with 16.67% discount: $1,490
  - Customer saves: $298 (2 months free)
```

### Scenario 2: 3 Months Free (Promotional)
```
Discount: 25%
Example (Business Plan):
  - Monthly: $399
  - Annual without discount: $399 × 12 = $4,788
  - Annual with 25% discount: $3,591
  - Customer saves: $1,197 (3 months free)
```

### Scenario 3: 1 Month Free (Conservative)
```
Discount: 8.33%
Example (Enterprise Plan):
  - Monthly: $1,499
  - Annual without discount: $1,499 × 12 = $17,988
  - Annual with 8.33% discount: $16,490
  - Customer saves: $1,498 (1 month free)
```

### Scenario 4: No Discount
```
Discount: 0%
Example:
  - Monthly: $149
  - Annual: $149 × 12 = $1,788
  - No savings
```

---

## 🎨 Admin Interface Features

### List View
The admin list view shows:
- **Plan Name**: e.g., "Startup"
- **Monthly Price**: e.g., "$149/mo"
- **Annual Price**: e.g., "$1,490/yr (Save $298)" in green
- **Discount**: e.g., "16.7% (2.0 months free)" in green
- **Requests**: e.g., "1M" (formatted)
- **Status**: Active/Inactive toggle

### Edit View
The edit form includes:
- **Basic Information**: Name, Type, Description
- **Pricing Section**: 
  - Monthly Price (manual input)
  - Annual Discount Percentage (manual input)
  - Annual Price (auto-calculated, shown for reference)
- **Quotas & Limits**: Requests, Apps, Users, Environments
- **Features**: Toggles for all features
- **Availability**: Active/Public toggles

### Visual Indicators
- **Green text**: Savings and discounts
- **Color-coded usage**: Green (<70%), Orange (70-90%), Red (>90%)
- **Formatted numbers**: 1M, 10M, 100M for readability

---

## 🔧 Technical Details

### Model Changes
```python
class SubscriptionPlan(BaseModel):
    # Existing fields...
    monthly_price = DecimalField(max_digits=10, decimal_places=2)
    annual_price = DecimalField(max_digits=10, decimal_places=2)
    
    # NEW FIELD
    annual_discount_percentage = DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=16.67,
        help_text="Discount % for annual billing. Set to 0 to disable."
    )
```

### Calculation Methods
```python
def calculate_annual_price(self):
    """Calculate annual price with discount"""
    if self.annual_discount_percentage > 0:
        annual_base = self.monthly_price * 12
        discount_amount = annual_base * (self.annual_discount_percentage / 100)
        return annual_base - discount_amount
    else:
        return self.monthly_price * 12

def get_annual_savings(self):
    """Get amount saved on annual vs monthly"""
    monthly_total = self.monthly_price * 12
    return monthly_total - self.calculate_annual_price()
```

### Auto-Save Hook
```python
def save(self, *args, **kwargs):
    """Auto-calculate annual price if discount is set"""
    if self.annual_discount_percentage > 0:
        self.annual_price = self.calculate_annual_price()
    super().save(*args, **kwargs)
```

---

## 📊 Current Plans Configuration

| Plan | Monthly | Discount | Annual | Savings | Equiv. Free Months |
|------|---------|----------|--------|---------|-------------------|
| **Free** | $0 | 0% | $0 | $0 | - |
| **Startup** | $149 | 16.67% | $1,490 | $298 | 2 months |
| **Business** | $399 | 16.67% | $3,990 | $798 | 2 months |
| **Enterprise** | $1,499 | 16.67% | $14,990 | $2,998 | 2 months |

---

## 🎯 Use Cases

### 1. Seasonal Promotions
**Black Friday / Holiday Sales**
- Temporarily increase discount to 25% (3 months free)
- Update all plans in admin
- Revert after promotion ends

### 2. Market Testing
**A/B Testing Different Discount Levels**
- Test 8.33% (1 month) vs 16.67% (2 months) vs 25% (3 months)
- Monitor conversion rates
- Adjust based on data

### 3. Competitive Response
**Match Competitor Pricing**
- Competitor offers 20% off? Quickly update to 20%
- No code deployment needed
- Immediate effect

### 4. Regional Pricing
**Different Discounts for Different Markets**
- Higher discount for emerging markets (25%)
- Standard discount for established markets (16.67%)
- Premium pricing with lower discount (8.33%)

### 5. Disable Discounts
**For Certain Plans or Temporarily**
- Set discount to 0%
- Annual price = Monthly × 12
- No promotional messaging

---

## 🔐 Access Control

### Who Can Modify Discounts?
Only users with **Django Admin access** and proper permissions:
- **Superusers**: Full access
- **Staff with permissions**: Can be granted specific permissions

### Recommended Permissions Setup:
1. **CEO/Finance**: Full access to all plans
2. **Product Manager**: View and edit plans
3. **Support Team**: Read-only access
4. **Engineers**: No access (use admin)

---

## 📈 Impact on Revenue

### Example: Changing Startup Plan Discount

**Current (16.67% discount)**:
- Annual price: $1,490
- 50 customers: $74,500/year

**If increased to 25%**:
- Annual price: $1,341
- 50 customers: $67,050/year
- **Loss**: $7,450/year
- **BUT**: Potentially higher conversion

**If decreased to 8.33%**:
- Annual price: $1,639
- 50 customers: $81,950/year
- **Gain**: $7,450/year
- **BUT**: Potentially lower conversion

---

## ⚠️ Important Notes

### Things to Remember:
1. **Changes are immediate** - take effect on next billing cycle
2. **Existing subscriptions** - Not retroactively changed (by design)
3. **Test in staging first** - Before production changes
4. **Document changes** - Keep record of why discount was changed
5. **Monitor impact** - Track conversion rates after changes

### Best Practices:
1. ✅ Make small changes (5-10% adjustments)
2. ✅ Test with small customer segment first
3. ✅ Document business rationale
4. ✅ Set calendar reminder to review results
5. ✅ Communicate changes to sales/support teams

### Don't:
1. ❌ Change discounts too frequently (confuses customers)
2. ❌ Make drastic changes (>10%) without testing
3. ❌ Forget to notify sales team
4. ❌ Change during active campaigns
5. ❌ Forget to check financial impact

---

## 🧪 Testing the Configuration

### 1. Access Admin:
```bash
# Create superuser (first time)
docker-compose exec backend python manage.py createsuperuser

# Access: http://localhost:8000/admin/
```

### 2. Modify a Plan:
- Go to Subscription Plans
- Click on "Startup"
- Change discount from 16.67% to 20%
- Save

### 3. Verify API Response:
```bash
curl http://localhost:8000/api/onboarding/plans/ | jq
```

### 4. Check Calculation:
- Monthly: $149
- Discount: 20%
- Expected Annual: $1,430.40
- Savings: $357.60

---

## 📱 API Response

Plans are returned via `/api/onboarding/plans/` with calculated values:

```json
{
  "plans": [
    {
      "name": "Startup",
      "monthly_price": "149.00",
      "annual_price": "1490.00",
      "max_requests_per_month": 1000000,
      "features": { ... }
    }
  ]
}
```

**Note**: `annual_price` is auto-calculated based on current discount percentage.

---

## 🎉 Benefits

### For Business Team:
✅ **Flexibility**: Change discounts without engineering
✅ **Speed**: Instant updates, no deployment
✅ **Testing**: Easy to run pricing experiments
✅ **Control**: Full visibility and management

### For Engineering Team:
✅ **No Code Changes**: Business logic abstracted
✅ **Maintainability**: Single source of truth
✅ **Auditability**: Django admin logs all changes
✅ **Scalability**: Easy to add more pricing models

### For Customers:
✅ **Competitive Pricing**: Business can respond to market
✅ **Promotional Offers**: Seasonal discounts possible
✅ **Transparency**: Clear savings calculation
✅ **Flexibility**: Options for annual commitment

---

## 🚀 Future Enhancements

Possible future additions:
1. **Time-based discounts**: Auto-expire on specific date
2. **Customer-specific discounts**: Override per organization
3. **Coupon codes**: Additional discounts via codes
4. **Volume discounts**: Different rates based on usage
5. **Regional pricing**: Different discounts per country

---

## 📞 Support

For questions or issues:
- **Technical**: Engineering team
- **Business**: Product/Finance team
- **Access**: IT/Admin team

---

**Last Updated**: November 2025  
**Version**: 1.0  
**Status**: ✅ Production Ready

