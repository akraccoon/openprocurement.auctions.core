# -*- coding: utf-8 -*-
from openprocurement.auctions.core.plugins.contracting.base.predicates import (
    not_active_lots_predicate
)

def validate_contract_document(request, operation):
    if (
        request.validated['auction_status']
        not in ['active.qualification', 'active.awarded']
    ):
        request.errors.add(
            'body',
            'data',
            'Can\'t {0} document in current ({1}) auction status'.format(
                operation,
                request.validated['auction_status']
            )
        )
        request.errors.status = 403
        return None
    if not_active_lots_predicate(request):
        request.errors.add(
            'body',
            'data',
            'Can {} document only in active lot status'.format(operation)
        )
        request.errors.status = 403
        return None
    if request.validated['contract'].status not in ['pending', 'active']:
        request.errors.add(
            'body',
            'data',
            'Can\'t {} document in current contract status'.format(
                operation
            )
        )
        request.errors.status = 403
        return None
    return True
