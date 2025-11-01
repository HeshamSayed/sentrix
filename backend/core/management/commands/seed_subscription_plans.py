"""
Seed subscription plans with realistic pricing
Based on actual operational costs in Egypt (Phase 1)

COST BREAKDOWN (Monthly in USD):

TEAM (7 people):
- 4 Engineers (Senior x2, Mid x2): $1,200 + $1,000 + $700 + $600 = $3,500
- 3 Security Specialists: $900 + $800 + $700 = $2,400
- 1 Marketing Specialist: $600
Total Salaries: $6,500/month

INFRASTRUCTURE:
- 1 Production Server (8 vCPU, 24GB RAM): $250/month
- Development/Staging Servers: $150/month
- Backup & Storage: $50/month
- CDN & DNS: $50/month
Total Infrastructure: $500/month

OFFICE & OPERATIONS:
- Office Rent (Cairo/Smart Village): $800/month
- Internet (Business Fiber): $100/month
- Utilities (Electricity, Water): $150/month
- Office Supplies & Equipment: $100/month
Total Office: $1,150/month

SOFTWARE & TOOLS:
- Development Tools (IDEs, Git, etc.): $100/month
- Monitoring & Analytics: $150/month
- Communication (Slack, Zoom, etc.): $50/month
- Security Tools: $100/month
Total Software: $400/month

MARKETING & SALES:
- Digital Marketing: $1,000/month
- Content Creation: $300/month
- Sales Tools: $100/month
Total Marketing: $1,400/month

LEGAL & ADMIN:
- Accounting & Legal: $200/month
- Insurance: $150/month
- Misc Admin: $100/month
Total Legal: $450/month

TOTAL MONTHLY COSTS: $10,400/month
YEARLY COSTS: $124,800/year

TAXES & CONTINGENCY:
- Corporate Tax (22.5% on profit): Variable
- Contingency (10%): $1,040/month
ADJUSTED TOTAL: $11,440/month ($137,280/year)

BREAK-EVEN ANALYSIS:
To cover costs: Need $11,440/month revenue minimum
Target profit margin: 50% = Need $22,880/month revenue
Healthy profit margin: 70% = Need $38,133/month revenue

SERVER CAPACITY: ~2.6B requests/month per server
"""

from django.core.management.base import BaseCommand
from core.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Seed subscription plans with realistic pricing based on Egypt operations'

    def handle(self, *args, **options):
        
        # Display cost breakdown
        self.stdout.write(
            self.style.SUCCESS('\n' + '='*70)
        )
        self.stdout.write(
            self.style.SUCCESS('SENTRIX EGYPT - COST BREAKDOWN (Phase 1)')
        )
        self.stdout.write(
            self.style.SUCCESS('='*70)
        )
        
        costs = {
            'Team Salaries': {
                '4 Engineers (2 Senior, 2 Mid)': 3500,
                '3 Security Specialists': 2400,
                '1 Marketing Specialist': 600,
                'Total': 6500
            },
            'Infrastructure': {
                'Production Server (8 vCPU, 24GB)': 250,
                'Dev/Staging Servers': 150,
                'Backup & Storage': 50,
                'CDN & DNS': 50,
                'Total': 500
            },
            'Office & Operations': {
                'Office Rent (Cairo)': 800,
                'Internet (Business)': 100,
                'Utilities': 150,
                'Office Supplies': 100,
                'Total': 1150
            },
            'Software & Tools': {
                'Development Tools': 100,
                'Monitoring & Analytics': 150,
                'Communication': 50,
                'Security Tools': 100,
                'Total': 400
            },
            'Marketing & Sales': {
                'Digital Marketing': 1000,
                'Content Creation': 300,
                'Sales Tools': 100,
                'Total': 1400
            },
            'Legal & Admin': {
                'Accounting & Legal': 200,
                'Insurance': 150,
                'Misc Admin': 100,
                'Total': 450
            }
        }
        
        total_monthly = 10400
        contingency = 1040
        total_with_contingency = 11440
        
        for category, items in costs.items():
            self.stdout.write(
                self.style.WARNING(f'\n{category}:')
            )
            for item, cost in items.items():
                if item == 'Total':
                    self.stdout.write(
                        self.style.SUCCESS(f'  {item}: ${cost:,}/month')
                    )
                else:
                    self.stdout.write(f'  • {item}: ${cost:,}/month')
        
        self.stdout.write(
            self.style.SUCCESS('\n' + '-'*70)
        )
        self.stdout.write(
            self.style.SUCCESS(f'TOTAL MONTHLY COSTS: ${total_monthly:,}/month')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Contingency (10%): ${contingency:,}/month')
        )
        self.stdout.write(
            self.style.SUCCESS(f'TOTAL WITH CONTINGENCY: ${total_with_contingency:,}/month')
        )
        self.stdout.write(
            self.style.SUCCESS(f'YEARLY COSTS: ${total_with_contingency * 12:,}/year')
        )
        self.stdout.write(
            self.style.SUCCESS('='*70)
        )
        
        # Pricing strategy
        self.stdout.write(
            self.style.WARNING('\nPRICING STRATEGY:')
        )
        self.stdout.write(f'  Break-even: ${total_with_contingency:,}/month')
        self.stdout.write(f'  Target (50% margin): ${int(total_with_contingency / 0.5):,}/month')
        self.stdout.write(f'  Healthy (70% margin): ${int(total_with_contingency / 0.3):,}/month')
        
        # Create subscription plans
        plans = [
            {
                'name': 'Free',
                'plan_type': 'free',
                'description': 'Perfect for testing and small projects. Community support only.',
                'monthly_price': 0,
                'annual_price': 0,
                'annual_discount_percentage': 0,  # No discount for free plan
                'max_requests_per_month': 10_000,  # Reduced - just for testing
                'max_applications': 1,
                'max_users': 1,
                'max_environments': 1,
                'behavioral_analysis': True,
                'real_time_blocking': True,
                'advanced_analytics': False,
                'custom_rules': False,
                'priority_support': False,
                'dedicated_resources': False,
                'sla_guarantee': False,
            },
            {
                'name': 'Startup',
                'plan_type': 'starter',
                'description': 'Perfect for startups and small teams. 14-day free trial. Email support.',
                'monthly_price': 149,
                'annual_discount_percentage': 16.67,  # 2 months free (configurable in admin)
                'max_requests_per_month': 1_000_000,  # 1M requests
                'max_applications': 5,
                'max_users': 3,
                'max_environments': 2,
                'behavioral_analysis': True,
                'real_time_blocking': True,
                'advanced_analytics': True,
                'custom_rules': False,
                'priority_support': False,
                'dedicated_resources': False,
                'sla_guarantee': False,
            },
            {
                'name': 'Business',
                'plan_type': 'professional',
                'description': 'For growing businesses. Priority support, advanced features, 99.9% SLA.',
                'monthly_price': 399,
                'annual_discount_percentage': 16.67,  # 2 months free (configurable in admin)
                'max_requests_per_month': 10_000_000,  # 10M requests
                'max_applications': 20,
                'max_users': 10,
                'max_environments': 4,
                'behavioral_analysis': True,
                'real_time_blocking': True,
                'advanced_analytics': True,
                'custom_rules': True,
                'priority_support': True,
                'dedicated_resources': False,
                'sla_guarantee': True,
            },
            {
                'name': 'Enterprise',
                'plan_type': 'enterprise',
                'description': 'For large organizations. Dedicated support, custom SLA, unlimited features.',
                'monthly_price': 1499,
                'annual_discount_percentage': 16.67,  # 2 months free (configurable in admin)
                'max_requests_per_month': 100_000_000,  # 100M requests
                'max_applications': 100,
                'max_users': 50,
                'max_environments': 10,
                'behavioral_analysis': True,
                'real_time_blocking': True,
                'advanced_analytics': True,
                'custom_rules': True,
                'priority_support': True,
                'dedicated_resources': True,
                'sla_guarantee': True,
            },
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'\nCreated plan: {plan.name} - ${plan.monthly_price}/month')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'\nUpdated plan: {plan.name} - ${plan.monthly_price}/month')
                )

        # Revenue scenarios
        self.stdout.write(
            self.style.SUCCESS('\n' + '='*70)
        )
        self.stdout.write(
            self.style.SUCCESS('REVENUE SCENARIOS (Per Month):')
        )
        self.stdout.write(
            self.style.SUCCESS('='*70)
        )
        
        scenarios = [
            {
                'name': 'Conservative (Reach in 6 months)',
                'mix': {
                    'Free': (50, 0),
                    'Startup': (20, 149),
                    'Business': (5, 399),
                    'Enterprise': (1, 1499),
                },
                'months': 6
            },
            {
                'name': 'Moderate (Reach in 12 months)',
                'mix': {
                    'Free': (100, 0),
                    'Startup': (50, 149),
                    'Business': (15, 399),
                    'Enterprise': (3, 1499),
                },
                'months': 12
            },
            {
                'name': 'Aggressive (Reach in 18 months)',
                'mix': {
                    'Free': (200, 0),
                    'Startup': (100, 149),
                    'Business': (30, 399),
                    'Enterprise': (8, 1499),
                },
                'months': 18
            }
        ]
        
        for scenario in scenarios:
            total_revenue = sum(count * price for count, price in scenario['mix'].values())
            total_customers = sum(count for count, _ in scenario['mix'].values())
            profit = total_revenue - total_with_contingency
            margin = (profit / total_revenue * 100) if total_revenue > 0 else 0
            
            self.stdout.write(
                self.style.WARNING(f'\n{scenario["name"]}:')
            )
            for plan_name, (count, price) in scenario['mix'].items():
                revenue = count * price
                self.stdout.write(f'  • {count}x {plan_name} = ${revenue:,}/month')
            
            self.stdout.write(
                self.style.SUCCESS(f'  Total Revenue: ${total_revenue:,}/month')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Total Customers: {total_customers}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Monthly Profit: ${profit:,}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Annual Profit: ${profit * 12:,}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'  Profit Margin: {margin:.1f}%')
            )
            
            if profit > 0:
                breakeven_months = (total_with_contingency * 3) / profit  # 3 months runway
                self.stdout.write(
                    self.style.SUCCESS(f'  Payback Period: {breakeven_months:.1f} months')
                )
        
        self.stdout.write(
            self.style.SUCCESS('\n' + '='*70)
        )
        self.stdout.write(
            self.style.SUCCESS('CAPACITY ANALYSIS:')
        )
        self.stdout.write(
            self.style.SUCCESS('='*70)
        )
        self.stdout.write('  Server Capacity: ~2.6B requests/month')
        self.stdout.write('  Conservative Scenario: 20 + 5 + 1 = 26 paying customers')
        self.stdout.write('    Total requests: ~30M/month (~1% capacity)')
        self.stdout.write('  Moderate Scenario: 50 + 15 + 3 = 68 paying customers')
        self.stdout.write('    Total requests: ~95M/month (~3.6% capacity)')
        self.stdout.write('  Aggressive Scenario: 100 + 30 + 8 = 138 paying customers')
        self.stdout.write('    Total requests: ~350M/month (~13% capacity)')
        self.stdout.write('\n  ✅ Excellent capacity for growth!')
        
        self.stdout.write(
            self.style.SUCCESS('\n' + '='*70)
        )
        self.stdout.write(
            self.style.SUCCESS('Successfully seeded subscription plans!')
        )
        self.stdout.write(
            self.style.SUCCESS('='*70 + '\n')
        )

