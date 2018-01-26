# -*- coding: utf-8 -*-
from datetime import timedelta

from openprocurement.api.models import get_now


# AuctionSwitchAuctionResourceTest


def switch_to_auction(self):
    response = self.set_status('active.auction', {'status': self.initial_status})
    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/auctions/{}'.format(self.auction_id), {'data': {'id': self.auction_id}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active.auction")

# AuctionSwitchUnsuccessfulResourceTest


def switch_to_unsuccessful(self):
    response = self.set_status('active.auction', {'status': self.initial_status})
    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/auctions/{}'.format(self.auction_id), {'data': {'id': self.auction_id}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "unsuccessful")
    if self.initial_lots:
        self.assertEqual(set([i['status'] for i in response.json['data']["lots"]]), set(["unsuccessful"]))

# AuctionComplaintSwitchResourceTest


def switch_to_pending(self):
    response = self.app.post_json('/auctions/{}/complaints'.format(self.auction_id), {'data': {
        'title': 'complaint title',
        'description': 'complaint description',
        'author': self.initial_organization,
        'status': 'claim'
    }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.json['data']['status'], 'claim')

    auction = self.db.get(self.auction_id)
    auction['complaints'][0]['dateSubmitted'] = (get_now() - timedelta(days=1 if 'procurementMethodDetails' in auction else 4)).isoformat()
    self.db.save(auction)

    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/auctions/{}'.format(self.auction_id), {'data': {'id': self.auction_id}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.json['data']["complaints"][0]['status'], 'pending')


def switch_to_complaint(self):
    for status in ['invalid', 'resolved', 'declined']:
        self.app.authorization = ('Basic', ('token', ''))
        response = self.app.post_json('/auctions/{}/complaints'.format(self.auction_id), {'data': {
            'title': 'complaint title',
            'description': 'complaint description',
            'author': self.initial_organization,
            'status': 'claim'
        }})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.json['data']['status'], 'claim')
        complaint = response.json['data']

        response = self.app.patch_json(
            '/auctions/{}/complaints/{}?acc_token={}'.format(self.auction_id, complaint['id'], self.auction_token),
            {"data": {
                "status": "answered",
                "resolution": status * 4,
                "resolutionType": status
            }})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "answered")
        self.assertEqual(response.json['data']["resolutionType"], status)

        auction = self.db.get(self.auction_id)
        auction['complaints'][-1]['dateAnswered'] = (
                get_now() - timedelta(days=1 if 'procurementMethodDetails' in auction else 4)).isoformat()
        self.db.save(auction)

        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/auctions/{}'.format(self.auction_id), {'data': {'id': self.auction_id}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']["complaints"][-1]['status'], status)

# AuctionAwardComplaintSwitchResourceTest


def switch_to_pending_award(self):
    response = self.app.post_json('/auctions/{}/awards/{}/complaints'.format(self.auction_id, self.award_id),
                                  {'data': {
                                      'title': 'complaint title',
                                      'description': 'complaint description',
                                      'author': self.initial_organization,
                                      'status': 'claim'
                                  }})
    self.assertEqual(response.status, '201 Created')
    self.assertEqual(response.json['data']['status'], 'claim')

    response = self.app.patch_json('/auctions/{}/awards/{}'.format(self.auction_id, self.award_id),
                                   {"data": {"status": "active"}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active")

    auction = self.db.get(self.auction_id)
    auction['awards'][0]['complaints'][0]['dateSubmitted'] = (
            get_now() - timedelta(days=1 if 'procurementMethodDetails' in auction else 4)).isoformat()
    self.db.save(auction)

    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/auctions/{}'.format(self.auction_id), {'data': {'id': self.auction_id}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.json['data']['awards'][0]["complaints"][0]['status'], 'pending')


def switch_to_complaint_award(self):
    response = self.app.patch_json('/auctions/{}/awards/{}'.format(self.auction_id, self.award_id),
                                   {"data": {"status": "active"}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active")

    for status in ['invalid', 'resolved', 'declined']:
        self.app.authorization = ('Basic', ('token', ''))
        response = self.app.post_json('/auctions/{}/awards/{}/complaints'.format(self.auction_id, self.award_id),
                                      {'data': {
                                          'title': 'complaint title',
                                          'description': 'complaint description',
                                          'author': self.initial_organization,
                                          'status': 'claim'
                                      }})
        self.assertEqual(response.status, '201 Created')
        self.assertEqual(response.json['data']['status'], 'claim')
        complaint = response.json['data']

        response = self.app.patch_json(
            '/auctions/{}/awards/{}/complaints/{}?acc_token={}'.format(self.auction_id, self.award_id, complaint['id'],
                                                                       self.auction_token), {"data": {
                "status": "answered",
                "resolution": status * 4,
                "resolutionType": status
            }})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['data']["status"], "answered")
        self.assertEqual(response.json['data']["resolutionType"], status)

        auction = self.db.get(self.auction_id)
        auction['awards'][0]['complaints'][-1]['dateAnswered'] = (
                get_now() - timedelta(days=1 if 'procurementMethodDetails' in auction else 4)).isoformat()
        self.db.save(auction)

        self.app.authorization = ('Basic', ('chronograph', ''))
        response = self.app.patch_json('/auctions/{}'.format(self.auction_id), {'data': {'id': self.auction_id}})
        self.assertEqual(response.status, '200 OK')
        self.assertEqual(response.json['data']['awards'][0]["complaints"][-1]['status'], status)

# AuctionDontSwitchSuspendedAuction2ResourceTest


def switch_suspended_auction_to_auction(self):
    self.app.authorization = ('Basic', ('administrator', ''))
    response = self.app.patch_json('/auctions/{}'.format(self.auction_id), {'data': {'suspended': True}})
    response = self.set_status('active.auction', {'status': self.initial_status})

    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/auctions/{}'.format(self.auction_id), {'data': {'id': self.auction_id}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertNotEqual(response.json['data']["status"], "active.auction")

    self.app.authorization = ('Basic', ('administrator', ''))
    response = self.app.patch_json('/auctions/{}'.format(self.auction_id), {'data': {'suspended': False}})

    self.app.authorization = ('Basic', ('chronograph', ''))
    response = self.app.patch_json('/auctions/{}'.format(self.auction_id), {'data': {'id': self.auction_id}})
    self.assertEqual(response.status, '200 OK')
    self.assertEqual(response.content_type, 'application/json')
    self.assertEqual(response.json['data']["status"], "active.auction")