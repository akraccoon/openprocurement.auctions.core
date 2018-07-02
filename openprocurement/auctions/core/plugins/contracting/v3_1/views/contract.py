# -*- coding: utf-8 -*-
from openprocurement.api.utils import get_now
from openprocurement.api.utils import (
    json_view,
    context_unpack,
    APIResource,
)
from openprocurement.auctions.core.utils import (
    apply_patch,
    save_auction,
    opresource,
    get_related_award_of_contract
)
from openprocurement.auctions.core.plugins.contracting.base.utils import (
    check_auction_status, check_document_existence
)
from openprocurement.auctions.core.validation import (
    validate_contract_data,
    validate_patch_contract_data,
)
from openprocurement.auctions.core.plugins.contracting.v3_1.validators import (
    validate_contract_create,
    validate_contract_update
)


@opresource(
    name='awarding_3_1:Auction Contracts',
    collection_path='/auctions/{auction_id}/contracts',
    path='/auctions/{auction_id}/contracts/{contract_id}',
    awardingType='awarding_3_1',
    description="Auction contracts"
)
class AuctionAwardContractResource(APIResource):

    @json_view(content_type="application/json", permission='create_contract', validators=(validate_contract_data, validate_contract_create))
    def collection_post(self):
        """Post a contract for award
        """
        auction = self.request.validated['auction']
        contract = self.request.validated['contract']
        auction.contracts.append(contract)
        if save_auction(self.request):
            self.LOGGER.info('Created auction contract {}'.format(contract.id),
                        extra=context_unpack(self.request, {'MESSAGE_ID': 'auction_contract_create'}, {'contract_id': contract.id}))
            self.request.response.status = 201
            route = self.request.matched_route.name.replace("collection_", "")
            self.request.response.headers['Location'] = self.request.current_route_url(_route_name=route, contract_id=contract.id, _query={})
            return {'data': contract.serialize()}

    @json_view(permission='view_auction')
    def collection_get(self):
        """List contracts for award
        """
        return {'data': [i.serialize() for i in self.request.context.contracts]}

    @json_view(permission='view_auction')
    def get(self):
        """Retrieving the contract for award
        """
        return {'data': self.request.validated['contract'].serialize()}

    @json_view(content_type="application/json", permission='edit_auction', validators=(validate_patch_contract_data, validate_contract_update))
    def patch(self):
        """Update of contract
        """
        auction = self.request.validated['auction']
        data = self.request.validated['data']
        now = get_now()

        if data['value']:
            for ro_attr in ('valueAddedTaxIncluded', 'currency'):
                if data['value'][ro_attr] != getattr(self.context.value, ro_attr):
                    self.request.errors.add('body', 'data', 'Can\'t update {} for contract value'.format(ro_attr))
                    self.request.errors.status = 403
                    return

            award = [a for a in auction.awards if a.id == self.request.context.awardID][0]
            if data['value']['amount'] < award.value.amount:
                self.request.errors.add('body', 'data', 'Value amount should be greater or equal to awarded amount ({})'.format(award.value.amount))
                self.request.errors.status = 403
                return

        if self.request.context.status == 'pending' and 'status' in data and data['status'] == 'cancelled':
            if not (check_document_existence(self.request.context, 'rejectionProtocol') or
                    check_document_existence(self.request.context, 'act')):
                self.request.errors.add(
                    'body',
                    'data',
                    'Can\'t switch contract status to (cancelled) before'
                    ' auction owner load reject protocol or act'
                )
                self.request.errors.status = 403
                return
            if check_document_existence(self.request.context, 'contractSigned'):
                self.request.errors.add('body', 'data', 'Bidder contract for whom has already been uploaded cannot be disqualified.')
                self.request.errors.status = 403
                return
            award = get_related_award_of_contract(self.request.context, auction)
            award.signingPeriod.endDate = now
            award.complaintPeriod.endDate = now
            award.status = 'unsuccessful'
            auction.awardPeriod.endDate = None
            auction.status = 'active.qualification'
            self.request.content_configurator.back_to_awarding()

        if self.request.context.status == 'pending' and 'status' in data and data['status'] == 'active':
            award = [a for a in auction.awards if a.id == self.request.context.awardID][0]
            stand_still_end = award.complaintPeriod.endDate
            if stand_still_end > now:
                self.request.errors.add('body', 'data', 'Can\'t sign contract before stand-still period end ({})'.format(stand_still_end.isoformat()))
                self.request.errors.status = 403
                return
            pending_complaints = [
                i
                for i in auction.complaints
                if i.status in ['claim', 'answered', 'pending'] and i.relatedLot in [None, award.lotID]
            ]
            pending_awards_complaints = [
                i
                for a in auction.awards
                for i in a.complaints
                if i.status in ['claim', 'answered', 'pending'] and a.lotID == award.lotID
            ]
            if pending_complaints or pending_awards_complaints:
                self.request.errors.add('body', 'data', 'Can\'t sign contract before reviewing all complaints')
                self.request.errors.status = 403
                return
            if not check_document_existence(self.request.context, 'contractSigned'):
                self.request.errors.add('body', 'data', 'Can\'t sign contract without contractSigned document')
                self.request.errors.status = 403
                return
            if not self.request.context.dateSigned:
                self.request.errors.add('body', 'data', 'Can\'t sign contract without specified dateSigned field')
                self.request.errors.status = 403
                return
        current_contract_status = self.request.context.status
        apply_patch(self.request, save=False, src=self.request.context.serialize())
        if current_contract_status != self.request.context.status and (current_contract_status == 'cancelled' or self.request.context.status == 'pending'):
            self.request.errors.add('body', 'data', 'Can\'t update contract status')
            self.request.errors.status = 403
            return
        check_auction_status(self.request)
        if save_auction(self.request):
            self.LOGGER.info('Updated auction contract {}'.format(self.request.context.id),
                        extra=context_unpack(self.request, {'MESSAGE_ID': 'auction_contract_patch'}))
            return {'data': self.request.context.serialize()}