from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Deal, Lead, User


class CRMEndpointsTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin1',
            password='StrongPass123!',
            role=User.Role.ADMIN,
            company_id=1,
        )
        refresh = RefreshToken.for_user(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    def test_leads_list_pagination(self):
        Lead.objects.create(
            company_id=1,
            first_name='Ivan',
            last_name='Petrov',
            phone='+79990000001',
            email='ivan@example.com',
            source='site',
            responsible=self.admin,
        )
        resp = self.client.get('/api/leads/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('results', resp.data)
        self.assertIn('count', resp.data)

    def test_convert_lead_to_deal(self):
        lead = Lead.objects.create(
            company_id=1,
            first_name='Maria',
            last_name='Ivanova',
            phone='+79990000002',
            source='call',
            budget=150000,
            responsible=self.admin,
        )
        resp = self.client.post(f'/api/leads/{lead.id}/convert/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertEqual(lead.status, Lead.Status.CONVERTED)
        self.assertTrue(Deal.objects.filter(lead=lead).exists())

    def test_close_lost_requires_reason(self):
        deal = Deal.objects.create(
            company_id=1,
            title='Test Deal',
            client_id=100,
            amount=10000,
            responsible=self.admin,
        )
        resp = self.client.post(f'/api/deals/{deal.id}/close-lost/', data={}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dashboard_summary_works(self):
        Lead.objects.create(
            company_id=1,
            first_name='Alex',
            last_name='Smirnov',
            phone='+79990000003',
            source='referral',
            responsible=self.admin,
        )
        resp = self.client.get('/api/dashboard/summary/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('leads_total', resp.data)
