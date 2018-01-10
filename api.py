# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4

from django.conf import settings

import hashlib
import binascii
import urllib
from Crypto.Cipher import DES3
from suds.client import Client
import logging

from .decorators import GPSettings

if settings.GOPAY_TEST:
    GOPAY_URL = 'http://testgw.gopay.cz/gw/pay-full-v2'
    GOPAY_WS = 'http://testgw.gopay.cz/axis/EPaymentServiceV2?wsdl'
#else:
#    GOPAY_URL = 'https://gate.gopay.cz/gw/pay-full-v2'
#    GOPAY_WS = 'https://gate.gopay.cz/axis/EPaymentServiceV2?wsdl'

logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.client').setLevel(logging.DEBUG)


class GoPayCommand(object):
    class NotImplemented(Exception):
        pass

    class InvalidArg(Exception):
        pass

    class InvalidSignature(Exception):
        pass

    def __init__(self, params={}):
        self.p = params
        self.c = Client(GOPAY_WS)

    def run(self):
        self.sign()
        cmd = self.create_command()
        ret = self.rpc(cmd)
        return ret

    def concat(self):
        raise self.NotImplemented('Concat neni implementovan pro tento prikaz')

    def create_command(self):
        raise self.NotImplemented('CreateCommand neni implementovan pro tento prikaz')

    def rpc(self, cmd):
        raise self.NotImplemented('RPC neni implementovan pro tento prikaz')

    def sign(self):
        cc = self.concat().encode('utf-8')
        h = hashlib.sha1(cc).hexdigest()
        des3 = DES3.new(settings.GOPAY_SECRET, DES3.MODE_ECB)
        e = des3.encrypt(h)
        s = binascii.b2a_hex(e)
        self.p['encryptedSignature'] = s

    def verifySignature(self):
        got = binascii.a2b_hex(self.p['encryptedSignature'])
        cc = self.concat().encode('utf-8')
        h = hashlib.sha1(cc).hexdigest()
        des3 = DES3.new(settings.GOPAY_SECRET, DES3.MODE_ECB)
        dh = des3.decrypt(got).strip("\x00")

        if h != dh:
            raise self.InvalidSignature('Neplatný podpis zprávy')


class PaymentCommand(GoPayCommand):
    class InvalidArg(Exception):
        pass

    class CallFailed(Exception):
        pass

    def __init__(self, *args, **kwargs):
        if type(kwargs['order']) != GPSettings.tx_model:
            raise self.InvalidArg('Neplatná objednávka')

        if getattr(kwargs['order'], GPSettings.tx_model.GPMeta.is_finished)():
            raise self.InvalidArg('Neplatná objednávka / již byla dokončena')

        if not getattr(kwargs['order'], GPSettings.tx_model.GPMeta.is_gp_payment)():
            raise self.InvalidArg('Neplatná objednávka / nejedná se o GoPay objednávku')

        if getattr(kwargs['order'], GPSettings.tx_model.GPMeta.payment_method).gopay_code is None:
            raise self.InvalidArg('Neplatný způsob platby')

        if not kwargs['user']:
            raise self.InvalidArg('Neplatný uživatel')

        afterSuccess = kwargs.get('afterSuccess', '')


        k = {
            'successURL': kwargs['urlSuccess'].strip(),
            'failedURL': kwargs['urlFail'].strip(),
            'productName': unicode(kwargs['description']).strip()[:128],
            'orderNumber': kwargs['order'].id,
            'totalPrice': int(kwargs['price'] * 100),
            'currency': 'CZK',
            'paymentChannels': str(getattr(kwargs['order'], GPSettings.tx_model.GPMeta.payment_method).gopay_code),
            'customerData.firstName': '',
            'customerData.lastName': '',
            'customerData.email': kwargs['email'][:128],
            'customerData.street': '',
            'customerData.city': '',
            'customerData.postalCode': '',
            'customerData.countryCode': 'CZE',
            'p1': afterSuccess,
        }

        super(PaymentCommand, self).__init__(k)

    def concat(self):
        return "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s" % (
            settings.GOPAY_ESHOP_ID,
            self.p['productName'],
            self.p['totalPrice'],
            self.p['currency'],
            self.p['orderNumber'],
            self.p['failedURL'],
            self.p['successURL'],
            '',
            '',
            '',
            '',
            '',
            self.p['paymentChannels'],
            settings.GOPAY_SECRET
        )

    def create_command(self):
        cmd = self.c.factory.create('{urn:AxisEPaymentProvider}EPaymentCommand')

        cmd.successURL = self.p['successURL']
        cmd.failedURL = self.p['failedURL']
        cmd.productName = self.p['productName']
        cmd.targetGoId = settings.GOPAY_ESHOP_ID
        cmd.orderNumber = self.p['orderNumber']
        cmd.totalPrice = self.p['totalPrice']
        cmd.currency = self.p['currency']
        cmd.paymentChannels = self.p['paymentChannels']
        cmd.encryptedSignature = self.p['encryptedSignature']
        cmd.customerData.firstName = self.p['customerData.firstName']
        cmd.customerData.lastName = self.p['customerData.lastName']
        cmd.customerData.email = self.p['customerData.email']
        cmd.customerData.street = self.p['customerData.street']
        cmd.customerData.city = self.p['customerData.city']
        cmd.customerData.postalCode = self.p['customerData.postalCode']
        cmd.customerData.countryCode = self.p['customerData.countryCode']
        if self.p['p1']:
            cmd.p1 = self.p['p1']

        return cmd

    def rpc(self, cmd):
        ps = PaymentStatus()
        ps.fillResponse(self.c.service.createPayment(cmd))
        if ps.p['result'] != 'CALL_COMPLETED':
            raise self.CallFailed(ps.p.get('resultDescription', 'No description'))
        return ps.p


class PaymentStatus(GoPayCommand):
    def fillResponse(self, response):
        self.p['paymentSessionId'] = response.paymentSessionId
        self.p['productName'] = unicode(response.productName)
        self.p['totalPrice'] = response.totalPrice
        self.p['currency'] = response.currency
        self.p['orderNumber'] = response.orderNumber
        self.p['recurrentPayment'] = True if response.recurrentPayment and response.recurrentPayment == 'true' else False
        self.p['parentPaymentSessionId'] = response.parentPaymentSessionId
        self.p['preAuthorization'] = response.preAuthorization
        self.p['result'] = response.result
        try:
            self.p['resultDescription'] = unicode(response.resultDescription)
        except AttributeError:
            pass
        self.p['sessionState'] = response.sessionState
        self.p['sessionSubState'] = response.sessionSubState
        self.p['paymentChannel'] = response.paymentChannel
        self.p['encryptedSignature'] = response.encryptedSignature

        self.verifySignature()

    def concat(self):
        # targetGoId|
        # productName|
        # totalPrice|
        # currency|
        # orderNumber|
        # recurrentPayment|
        # parentPaymentSessionId|
        # preAuthorization|
        # result|
        # sessionState|
        # sessionSubState|
        # paymentChannel|
        # secureKey
        return "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s" % (
            settings.GOPAY_ESHOP_ID,
            self.p['productName'],
            self.p['totalPrice'],
            self.p['currency'],
            self.p['orderNumber'],
            self.p['recurrentPayment'] or '',
            self.p['parentPaymentSessionId'] or '',
            self.p['preAuthorization'] or '',
            self.p['result'],
            self.p['sessionState'],
            self.p['sessionSubState'] or '',
            self.p['paymentChannel'] or '',
            settings.GOPAY_SECRET
        )


class PaymentSession(GoPayCommand):
    def __init__(self, *args, **kwargs):
        if type(kwargs['order']) != GPSettings.tx_model:
            raise self.InvalidArg('Neplatná objednávka')

        if not getattr(kwargs['order'], GPSettings.tx_model.GPMeta.is_gp_payment)():
            raise self.InvalidArg('Neplatná objednávka / nejedná se o GoPay objednávku')

        if not getattr(kwargs['order'], GPSettings.tx_model.GPMeta.payment_session_id):
            raise self.InvalidArg('Neexistuje vazba na platbu v GoPay')

        k = {
            'paymentSessionId': getattr(kwargs['order'], GPSettings.tx_model.GPMeta.payment_session_id),
            'targetGoId': settings.GOPAY_ESHOP_ID,
        }
        super(PaymentSession, self).__init__(k)

    def concat(self):
        return "%s|%s|%s" % (
            settings.GOPAY_ESHOP_ID,
            self.p['paymentSessionId'],
            settings.GOPAY_SECRET
        )

    def create_url(self):
        # https://gate.gopay.cz/gw/pay-full-v2?
        # sessionInfo.paymentSessionId=3803928540&
        # sessionInfo.targetGoId=1803628540&
        # sessionInfo.encryptedSignature=25ee53a1eccc253a8317bc9487174d09ba6b00a0f5267d2de6b483f58af9676d883e26600ce3316a

        self.sign()
        p = {
            'sessionInfo.paymentSessionId': self.p['paymentSessionId'],
            'sessionInfo.targetGoId': self.p['targetGoId'],
            'sessionInfo.encryptedSignature': self.p['encryptedSignature'],
        }

        params = urllib.urlencode(p)
        return "%s?%s" % (GOPAY_URL, params)

    def create_command(self):
        cmd = self.c.factory.create('{urn:AxisEPaymentProvider}EPaymentSessionInfo')
        cmd.targetGoId = settings.GOPAY_ESHOP_ID
        cmd.paymentSessionId = self.p['paymentSessionId']
        cmd.encryptedSignature = self.p['encryptedSignature']

        return cmd

    def rpc(self, cmd):
        ps = PaymentStatus()
        ps.fillResponse(self.c.service.paymentStatus(cmd))
        if ps.p['result'] != 'CALL_COMPLETED':
            raise self.CallFailed(ps.p.get('resultDescription', 'No description'))
        return ps.p


class PaymentIdentity(GoPayCommand):
    def fillRequest(self, request):
        self.p['paymentSessionId'] = request.GET.get('paymentSessionId', None)
        self.p['targetGoId'] = request.GET.get('targetGoId', None)
        self.p['orderNumber'] = request.GET.get('orderNumber', None)
        self.p['parentPaymentSessionId'] = request.GET.get('parentPaymentSessionId', None)
        self.p['encryptedSignature'] = request.GET.get('encryptedSignature', None)
        self.p['afterSuccess'] = request.GET.get('p1', '')

        self.verifySignature()

    def concat(self):
        return "%s|%s|%s|%s|%s" % (
            settings.GOPAY_ESHOP_ID,
            self.p['paymentSessionId'],
            self.p['parentPaymentSessionId'] or '',
            self.p['orderNumber'],
            settings.GOPAY_SECRET
        )


def create_payment(request, urlReturn, order, description, price, email, afterSuccess=None):
    returnUrl = request.build_absolute_uri(urlReturn)

    gp = PaymentCommand(
        order=order,
        user=request.user,
        email=email,
        urlSuccess=returnUrl,
        urlFail=returnUrl,
        description=description,
        price=price,
        afterSuccess=afterSuccess
    )
    gpres = gp.run()
    return str(gpres['paymentSessionId'])


def get_redir(order):
    return PaymentSession(order=order).create_url()


def process_get_params(request):
    pi = PaymentIdentity()
    pi.fillRequest(request)

    """
    o = GPSettings.tx_model.objects_default.filter(**{
        GPSettings.tx_model.GPMeta.payment_session_id: pi.p['paymentSessionId']
    }).for_update()[0]
    """
    o = GPSettings.tx_model.objects_default.filter(**{
        GPSettings.tx_model.GPMeta.payment_session_id: pi.p['paymentSessionId']
    })[0]

    paysession = PaymentSession(order=o)
    return (o, paysession.run())
